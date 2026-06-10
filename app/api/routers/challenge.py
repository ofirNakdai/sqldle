from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app import schemas
from app.db import models
from app.db.db import get_db
from app.services.ai_challenge import ChallengeGenerationError, generate_challenge

router = APIRouter()


def _to_out(challenge: models.Challenge) -> schemas.ChallengeOut:
    """Map a `Challenge` ORM instance to the `ChallengeOut` API schema."""
    return schemas.ChallengeOut.model_validate(
        {
            "id": challenge.id,
            "slug": challenge.slug,
            "title": challenge.title,
            "difficulty": challenge.difficulty.value,
            "topics": [t.slug for t in challenge.topics],
            "estimated_minutes": challenge.estimated_minutes,
            "prompt": challenge.prompt,
            "schema": challenge.schema_tables,
            "expected_columns": challenge.expected_columns,
            "expected_rows": challenge.expected_rows,
            "starter_sql": challenge.starter_sql,
            "hints": [{"id": h.id, "text": h.text} for h in challenge.hints],
            "editorial": challenge.editorial,
        }
    )


def _pick_new_daily(db: Session) -> models.Challenge:
    """Pick a challenge that has never been used as a daily; fall back to any."""
    used = db.query(models.DailyChallenge.challenge_id)
    candidate = (
        db.query(models.Challenge)
        .filter(~models.Challenge.id.in_(used))
        .order_by(models.Challenge.slug)
        .first()
    )
    if candidate is None:
        candidate = db.query(models.Challenge).order_by(models.Challenge.slug).first()
    if candidate is None:
        raise HTTPException(status_code=404, detail="No challenges available")
    return candidate


@router.get("", response_model=list[schemas.ChallengeOut])
def list_challenges(db: Session = Depends(get_db)) -> list[schemas.ChallengeOut]:
    challenges = db.query(models.Challenge).order_by(models.Challenge.slug).all()
    return [_to_out(c) for c in challenges]


@router.post(
    "/generate",
    response_model=schemas.ChallengeOut,
    status_code=201,
)
def generate_ai_challenge(
    body: schemas.ChallengeGenerateRequest | None = None,
    db: Session = Depends(get_db),
) -> schemas.ChallengeOut:
    """Ask the AI agent to author a new challenge and persist it."""
    req = body or schemas.ChallengeGenerateRequest()
    try:
        challenge = generate_challenge(
            db,
            difficulty=req.difficulty,
            topics=req.topics,
            tables=req.tables,
            theme=req.theme,
        )
    except ChallengeGenerationError as exc:
        db.rollback()
        # 503: feature not configured; 422: model produced unusable output.
        status = 503 if "not configured" in str(exc) else 422
        raise HTTPException(status_code=status, detail=str(exc)) from exc

    return _to_out(challenge)


@router.get("/daily", response_model=schemas.DailyChallengeOut)
def get_daily_challenge(db: Session = Depends(get_db)) -> schemas.DailyChallengeOut:
    today_row = (
        db.query(models.DailyChallenge)
        .filter(models.DailyChallenge.day == models.func.current_date())
        .one_or_none()
    )
    if today_row is None:
        picked = _pick_new_daily(db)
        today_row = models.DailyChallenge(
            day=models.func.current_date(), challenge_id=picked.id
        )
        db.add(today_row)
        db.commit()
        db.refresh(today_row)

    return schemas.DailyChallengeOut.model_validate(
        {"date": today_row.day, "challenge": _to_out(today_row.challenge)}
    )


@router.get("/{key}", response_model=schemas.ChallengeOut)
def get_challenge(key: str, db: Session = Depends(get_db)) -> schemas.ChallengeOut:
    challenge = (
        db.query(models.Challenge)
        .filter(or_(models.Challenge.id == key, models.Challenge.slug == key))
        .one_or_none()
    )
    if challenge is None:
        raise HTTPException(status_code=404, detail="Challenge not found")
    return _to_out(challenge)
