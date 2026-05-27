from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import schemas
from app.db import models
from app.db.db import get_db

router = APIRouter()

def get_new_daily_challenge(db: Session) -> models.Challenge:
    """Select a new daily challenge from the pool of non-daily challenges."""
    # Get all challenges that are not currently set as the daily challenge
    subquery = db.query(models.DailyChallenge.challenge_id)
    candidates = db.query(models.Challenge).filter(~models.Challenge.id.in_(subquery)).all()
    
    if not candidates:
        raise HTTPException(status_code=404, detail="No available challenges for daily selection")
    
    # For simplicity, just pick the first candidate; could be randomized or use other logic
    return candidates[0]

def _to_out(challenge: models.Challenge) -> schemas.ChallengeOut:
    """Map a `Challenge` ORM instance to the `ChallengeOut` API schema.

    Bridges ORM/JSONB differences from the wire format:
    - `topics` is a relationship to `Topic` rows; the API returns slug strings.
    - `schema_tables` (JSONB) is exposed as `schema` on the wire.
    - `hints` is a relationship; only `id` and `text` are surfaced.
    """
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


@router.get("/", response_model=list[schemas.ChallengeOut])
def list_challenges(db: Session = Depends(get_db)) -> list[schemas.ChallengeOut]:
    print("Listing challenges...")
    challenges = db.query(models.Challenge).order_by(models.Challenge.slug).all()
    return [_to_out(c) for c in challenges]


@router.get("/daily", response_model=schemas.DailyChallengeOut)
def get_daily_challenge(db: Session = Depends(get_db)) -> schemas.DailyChallengeOut:
    res_challenge = db.query(models.DailyChallenge).where(models.DailyChallenge.day == models.func.current_date()).one_or_none()
    if res_challenge is None:
        try:
            # Means no daily challenge has been set for today
            res_challenge = get_new_daily_challenge(db)
            print(f"Selected new daily challenge: {res_challenge.slug}")
            res_challenge = models.DailyChallenge(day=models.func.current_date(), challenge_id=res_challenge.id)
            db.add(res_challenge)
            db.commit()
        except HTTPException as he:
            raise he
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))        
    return {"date": res_challenge.day, "challenge": _to_out(res_challenge.challenge)}

@router.get("/{slug}", response_model=schemas.ChallengeOut)
def get_challenge(slug: str, db: Session = Depends(get_db)) -> schemas.ChallengeOut:
    challenge = (
        db.query(models.Challenge).filter(models.Challenge.slug == slug).one_or_none()
    )
    if challenge is None:
        raise HTTPException(status_code=404, detail="Challenge not found")
    return _to_out(challenge)


