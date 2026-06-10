from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app import schemas
from app.db import models
from app.db.db import get_db

router = APIRouter()


def _to_out(track: models.Track) -> schemas.TrackOut:
    """Map a `Track` ORM instance to the `TrackOut` API schema."""
    return schemas.TrackOut.model_validate(
        {
            "id": track.id,
            "slug": track.slug,
            "title": track.title,
            "tagline": track.tagline,
            "description": track.description,
            "difficulty": track.difficulty.value,
            "topics": [t.slug for t in track.topics],
            "lessons": [
                {
                    "id": l.id,
                    "title": l.title,
                    "summary": l.summary,
                    "topics": [t.slug for t in l.topics],
                    "challenge_ids": [c.challenge_id for c in l.challenges],
                }
                for l in track.lessons
            ],
        }
    )


@router.get("", response_model=list[schemas.TrackOut])
def list_tracks(db: Session = Depends(get_db)) -> list[schemas.TrackOut]:
    tracks = db.query(models.Track).all()
    return [_to_out(t) for t in tracks]


@router.get("/{key}", response_model=schemas.TrackOut)
def get_track(key: str, db: Session = Depends(get_db)) -> schemas.TrackOut:
    track = (
        db.query(models.Track)
        .filter(or_(models.Track.id == key, models.Track.slug == key))
        .one_or_none()
    )
    if track is None:
        raise HTTPException(status_code=404, detail="Track not found")
    return _to_out(track)
