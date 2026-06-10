"""Submission endpoint.

Runs the user-supplied SQL against the same database (read-only restriction
enforced by syntactic check), compares against the challenge's expected
result, and stores the submission for the demo user.
"""
from __future__ import annotations

import json
import re
import time
from datetime import date, datetime, time as dt_time, timezone
from decimal import Decimal
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app import schemas
from app.db import models
from app.db.db import get_db
from app.db.sandboxes import SANDBOX_SCHEMA, sandbox_exists

router = APIRouter()

# Single-user MVP: the demo user seeded into the DB.
DEMO_USER_ID = "u1"

# Only SELECT or WITH ... SELECT statements may be executed.
_SELECT_RE = re.compile(r"^\s*(select|with)\b", re.IGNORECASE)
_FORBIDDEN_RE = re.compile(
    r"\b(insert|update|delete|drop|alter|truncate|create|grant|revoke|comment|"
    r"vacuum|reindex|cluster|copy|call|do|merge)\b",
    re.IGNORECASE,
)


def _json_default(value: Any) -> Any:
    if isinstance(value, Decimal):
        # Preserve int when there's no fractional part so `Decimal('660.0')`
        # compares equal to the JSON integer `660` in expected_rows.
        return int(value) if value == value.to_integral_value() else float(value)
    if isinstance(value, (datetime, date, dt_time)):
        # Canonical ISO-8601 ("2025-11-12T10:00:00"), matching expected_rows.
        return value.isoformat()
    return str(value)


def _normalize(value: Any) -> Any:
    """JSON round-trip so Decimal/datetime/date compare against seed data."""
    return json.loads(json.dumps(value, default=_json_default))


def _is_read_only(sql: str) -> bool:
    """Cheap syntactic check: must start with SELECT/WITH and contain no DDL/DML."""
    # Strip trailing semicolons and only allow a single statement.
    stripped = sql.strip().rstrip(";").strip()
    if ";" in stripped:
        return False
    if not _SELECT_RE.match(stripped):
        return False
    if _FORBIDDEN_RE.search(stripped):
        return False
    return True


def _evaluate(
    submission: schemas.SubmissionCreate, db: Session
) -> tuple[schemas.SubmissionResultOut, models.SubmissionStatus]:
    challenge = (
        db.query(models.Challenge)
        .filter(models.Challenge.id == submission.challenge_id)
        .one_or_none()
    )
    if challenge is None:
        raise HTTPException(status_code=404, detail="Challenge not found")

    sub_id = f"sub_{uuid4().hex[:12]}"
    created_at = datetime.now(timezone.utc)

    if not _is_read_only(submission.sql):
        return (
            schemas.SubmissionResultOut(
                id=sub_id,
                challenge_id=challenge.id,
                status="error",
                message="Only a single SELECT or WITH ... SELECT statement is allowed.",
                columns=None,
                rows_returned=None,
                duration_ms=0,
                created_at=created_at,
            ),
            models.SubmissionStatus.error,
        )

    schema = SANDBOX_SCHEMA
    if not sandbox_exists(db, schema):
        return (
            schemas.SubmissionResultOut(
                id=sub_id,
                challenge_id=challenge.id,
                status="error",
                message=(
                    f"Sandbox '{schema}' has not been built yet. "
                    "Run `python -m app.db.sandboxes`."
                ),
                columns=None,
                rows_returned=None,
                duration_ms=0,
                created_at=created_at,
            ),
            models.SubmissionStatus.error,
        )

    start = time.perf_counter()
    try:
        # SET LOCAL only persists for the current transaction, so the rollback
        # below restores the connection's default search_path.
        db.execute(text(f'SET LOCAL search_path TO "{schema}"'))
        result = db.execute(text(submission.sql))
        columns = list(result.keys())
        rows = [list(r) for r in result.fetchall()]
    except Exception as exc:  # noqa: BLE001
        duration_ms = int((time.perf_counter() - start) * 1000)
        return (
            schemas.SubmissionResultOut(
                id=sub_id,
                challenge_id=challenge.id,
                status="error",
                message=f"SQL error: {exc}",
                columns=None,
                rows_returned=None,
                duration_ms=duration_ms,
                created_at=created_at,
            ),
            models.SubmissionStatus.error,
        )
    finally:
        # SELECT-only, but rollback also clears the SET LOCAL search_path.
        db.rollback()

    duration_ms = int((time.perf_counter() - start) * 1000)

    expected_columns = [c.lower() for c in challenge.expected_columns]
    actual_columns = [c.lower() for c in columns]
    norm_rows = _normalize(rows)
    norm_expected = _normalize(challenge.expected_rows)

    if actual_columns == expected_columns and norm_rows == norm_expected:
        status, model_status, message = "pass", models.SubmissionStatus.pass_, "Correct solution!"
    elif actual_columns == expected_columns:
        status, model_status, message = (
            "fail",
            models.SubmissionStatus.fail,
            "Columns match but rows do not.",
        )
    else:
        status, model_status, message = (
            "fail",
            models.SubmissionStatus.fail,
            "Columns do not match the expected output.",
        )

    return (
        schemas.SubmissionResultOut(
            id=sub_id,
            challenge_id=challenge.id,
            status=status,
            message=message,
            columns=columns,
            rows_returned=rows,
            duration_ms=duration_ms,
            created_at=created_at,
        ),
        model_status,
    )


def _persist(
    result: schemas.SubmissionResultOut,
    sql: str,
    model_status: models.SubmissionStatus,
    db: Session,
) -> None:
    """Best-effort persistence; failures don't break the response."""
    try:
        # Skip if there is no demo user (e.g. running against an empty DB).
        user = db.query(models.User).filter(models.User.id == DEMO_USER_ID).one_or_none()
        if user is None:
            return

        row = models.Submission(
            id=result.id,
            user_id=DEMO_USER_ID,
            challenge_id=result.challenge_id,
            sql=sql,
            status=model_status,
            message=result.message,
            duration_ms=result.duration_ms,
            columns=result.columns,
            rows_returned=result.rows_returned,
            created_at=result.created_at,
        )
        db.add(row)

        # Bump user stats on a pass.
        if model_status == models.SubmissionStatus.pass_:
            already_passed = (
                db.query(models.Submission)
                .filter(
                    models.Submission.user_id == DEMO_USER_ID,
                    models.Submission.challenge_id == result.challenge_id,
                    models.Submission.status == models.SubmissionStatus.pass_,
                    models.Submission.id != result.id,
                )
                .first()
            )
            if already_passed is None:
                user.total_solved = (user.total_solved or 0) + 1
                user.xp = (user.xp or 0) + 50

        db.commit()
    except Exception:  # noqa: BLE001
        db.rollback()


@router.post("", response_model=schemas.SubmissionResultOut)
def submit_solution(
    submission: schemas.SubmissionCreate, db: Session = Depends(get_db)
) -> schemas.SubmissionResultOut:
    result, model_status = _evaluate(submission, db)
    _persist(result, submission.sql, model_status, db)
    return result
