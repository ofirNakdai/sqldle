"""Interview session endpoints.

Creates a timed practice session of random challenges at the requested
difficulty and exposes lookup + finish operations.
"""
from __future__ import annotations

import random
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import schemas
from app.db import models
from app.db.db import get_db

router = APIRouter()

DEMO_USER_ID = "u1"

# Seconds budgeted per question per difficulty.
_TIME_PER_QUESTION: dict[str, int] = {
    "easy": 60,
    "medium": 120,
    "hard": 180,
    "expert": 240,
}


def _to_out(session: models.InterviewSession) -> schemas.InterviewSessionOut:
    return schemas.InterviewSessionOut.model_validate(
        {
            "id": session.id,
            "difficulty": session.difficulty.value,
            "challenge_ids": [q.challenge_id for q in session.questions],
            "time_limit_sec": session.time_limit_sec,
            "created_at": session.started_at,
        }
    )


def _ensure_user(db: Session) -> models.User:
    user = (
        db.query(models.User)
        .filter(models.User.id == DEMO_USER_ID)
        .one_or_none()
    )
    if user is None:
        raise HTTPException(status_code=404, detail="Demo user not found")
    return user


@router.post("", response_model=schemas.InterviewSessionOut, status_code=201)
def create_interview_session(
    payload: schemas.InterviewSessionCreate, db: Session = Depends(get_db)
) -> schemas.InterviewSessionOut:
    user = _ensure_user(db)

    difficulty_enum = models.Difficulty(payload.difficulty)
    pool = (
        db.query(models.Challenge)
        .filter(models.Challenge.difficulty == difficulty_enum)
        .all()
    )
    if not pool:
        raise HTTPException(
            status_code=404,
            detail=f"No challenges available for difficulty '{payload.difficulty}'",
        )

    count = min(payload.question_count, len(pool))
    chosen = random.sample(pool, count)

    session = models.InterviewSession(
        id=f"is_{uuid4().hex[:12]}",
        user_id=user.id,
        difficulty=difficulty_enum,
        time_limit_sec=_TIME_PER_QUESTION[payload.difficulty] * count,
        started_at=datetime.now(timezone.utc),
    )
    for i, challenge in enumerate(chosen):
        session.questions.append(
            models.InterviewQuestion(position=i, challenge_id=challenge.id)
        )
    db.add(session)
    db.commit()
    db.refresh(session)
    return _to_out(session)


@router.get("/{session_id}", response_model=schemas.InterviewSessionOut)
def get_interview_session(
    session_id: str, db: Session = Depends(get_db)
) -> schemas.InterviewSessionOut:
    session = (
        db.query(models.InterviewSession)
        .filter(models.InterviewSession.id == session_id)
        .one_or_none()
    )
    if session is None:
        raise HTTPException(status_code=404, detail="Interview session not found")
    return _to_out(session)


@router.post("/{session_id}/finish", response_model=schemas.InterviewSessionOut)
def finish_interview_session(
    session_id: str, db: Session = Depends(get_db)
) -> schemas.InterviewSessionOut:
    session = (
        db.query(models.InterviewSession)
        .filter(models.InterviewSession.id == session_id)
        .one_or_none()
    )
    if session is None:
        raise HTTPException(status_code=404, detail="Interview session not found")

    if session.finished_at is None:
        session.finished_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(session)
    return _to_out(session)
