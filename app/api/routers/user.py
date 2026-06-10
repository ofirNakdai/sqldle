"""User progress endpoint."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import schemas
from app.db import models
from app.db.db import get_db

router = APIRouter()

# Single signed-in user for MVP.
DEMO_USER_ID = "u1"


@router.get("/progress", response_model=schemas.UserProgressOut)
def get_user_progress(db: Session = Depends(get_db)) -> schemas.UserProgressOut:
    user = (
        db.query(models.User)
        .filter(models.User.id == DEMO_USER_ID)
        .one_or_none()
    )
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    masteries = (
        db.query(models.TopicMastery)
        .filter(models.TopicMastery.user_id == user.id)
        .all()
    )

    achievement_rows = (
        db.query(models.UserAchievement, models.Achievement)
        .join(
            models.Achievement,
            models.UserAchievement.achievement_id == models.Achievement.id,
        )
        .filter(models.UserAchievement.user_id == user.id)
        .all()
    )

    recent = (
        db.query(models.Submission)
        .filter(models.Submission.user_id == user.id)
        .order_by(models.Submission.created_at.desc())
        .limit(10)
        .all()
    )

    track_progs = (
        db.query(models.TrackProgress)
        .filter(models.TrackProgress.user_id == user.id)
        .all()
    )

    return schemas.UserProgressOut.model_validate(
        {
            "user": {
                "id": user.id,
                "display_name": user.display_name,
                "avatar_color": user.avatar_color,
            },
            "total_solved": user.total_solved,
            "current_streak": user.current_streak,
            "best_streak": user.best_streak,
            "xp": user.xp,
            "level": user.level,
            "topic_mastery": [
                {"topic": tm.topic.slug, "mastery": tm.mastery} for tm in masteries
            ],
            "recent_submissions": [
                {
                    "id": s.id,
                    "challenge_id": s.challenge_id,
                    "status": s.status.value,
                    "message": s.message,
                    "columns": s.columns,
                    "rows_returned": s.rows_returned,
                    "duration_ms": s.duration_ms,
                    "created_at": s.created_at,
                }
                for s in recent
            ],
            "achievements": [
                {
                    "id": a.id,
                    "title": a.title,
                    "description": a.description,
                    "icon": a.icon.value,
                    "unlocked_at": ua.unlocked_at,
                }
                for ua, a in achievement_rows
            ],
            "track_progress": [
                {
                    "track_id": tp.track_id,
                    "completed": tp.completed_lessons,
                    "total": tp.total_lessons,
                }
                for tp in track_progs
            ],
        }
    )
