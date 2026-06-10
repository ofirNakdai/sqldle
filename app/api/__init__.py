from app.api.routers.challenge import router as challenge_router
from app.api.routers.track import router as track_router
from app.api.routers.submissions import router as submissions_router
from app.api.routers.user import router as user_router
from app.api.routers.interview_sessions import router as interview_sessions_router

__all__ = [
    "challenge_router",
    "track_router",
    "submissions_router",
    "user_router",
    "interview_sessions_router",
]
