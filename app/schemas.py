"""Pydantic v2 schemas matching the frontend `ApiClient` contract.

Field aliases convert Python snake_case to the camelCase the React app expects,
so these models can be returned directly from FastAPI endpoints.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Literals (match TypeScript unions exactly)
# ---------------------------------------------------------------------------

Difficulty = Literal["easy", "medium", "hard", "expert"]

SqlTopic = Literal[
    "basics",
    "filtering",
    "joins",
    "aggregation",
    "subqueries",
    "window-functions",
    "ctes",
    "indexing",
    "performance",
    "modeling",
    "transactions",
]

SubmissionStatus = Literal["pass", "fail", "error"]
AchievementIcon = Literal["flame", "trophy", "target", "zap", "crown"]


class CamelModel(BaseModel):
    """Base model that emits camelCase JSON and accepts both casings as input."""

    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
        alias_generator=lambda s: _to_camel(s),
    )


def _to_camel(s: str) -> str:
    parts = s.split("_")
    return parts[0] + "".join(p.title() for p in parts[1:])


# ---------------------------------------------------------------------------
# Challenge
# ---------------------------------------------------------------------------


class SchemaColumn(CamelModel):
    name: str
    type: str
    note: str | None = None


class TableSchema(CamelModel):
    name: str
    columns: list[SchemaColumn]
    sample_rows: list[dict[str, Any]] = Field(default_factory=list)


class HintOut(CamelModel):
    id: str
    text: str


class ChallengeOut(CamelModel):
    id: str
    slug: str
    title: str
    difficulty: Difficulty
    topics: list[SqlTopic]
    estimated_minutes: int
    prompt: str
    schema_: list[TableSchema] = Field(serialization_alias="schema", alias="schema")
    expected_columns: list[str]
    expected_rows: list[list[Any]]
    starter_sql: str | None = None
    hints: list[HintOut]
    editorial: str


class DailyChallengeOut(CamelModel):
    date: date
    challenge: ChallengeOut


class ChallengeGenerateRequest(CamelModel):
    """Optional steering for AI challenge generation. All fields optional."""

    difficulty: Difficulty | None = None
    topics: list[SqlTopic] = Field(default_factory=list)
    tables: list[str] = Field(default_factory=list)
    theme: str | None = Field(
        default=None,
        description="Freeform guidance for the kind of challenge to create.",
    )


# ---------------------------------------------------------------------------
# Track / lesson
# ---------------------------------------------------------------------------


class LessonOut(CamelModel):
    id: str
    title: str
    summary: str
    topics: list[SqlTopic]
    challenge_ids: list[str]


class TrackOut(CamelModel):
    id: str
    slug: str
    title: str
    tagline: str
    description: str
    difficulty: Difficulty
    topics: list[SqlTopic]
    lessons: list[LessonOut]


# ---------------------------------------------------------------------------
# Submission
# ---------------------------------------------------------------------------


class SubmissionCreate(CamelModel):
    challenge_id: str
    sql: str


class SubmissionResultOut(CamelModel):
    id: str
    challenge_id: str
    status: SubmissionStatus
    message: str
    columns: list[str] | None = None
    rows_returned: list[list[Any]] | None = None
    duration_ms: int
    created_at: datetime


# ---------------------------------------------------------------------------
# User & progress
# ---------------------------------------------------------------------------


class UserPublic(CamelModel):
    id: str
    display_name: str
    avatar_color: str


class TopicMasteryOut(CamelModel):
    topic: SqlTopic
    mastery: float


class AchievementOut(CamelModel):
    id: str
    title: str
    description: str
    icon: AchievementIcon
    unlocked_at: datetime | None = None


class TrackProgressOut(CamelModel):
    track_id: str
    completed: int
    total: int


class UserProgressOut(CamelModel):
    user: UserPublic
    total_solved: int
    current_streak: int
    best_streak: int
    xp: int
    level: int
    topic_mastery: list[TopicMasteryOut]
    recent_submissions: list[SubmissionResultOut]
    achievements: list[AchievementOut]
    track_progress: list[TrackProgressOut]


# ---------------------------------------------------------------------------
# Interview sessions
# ---------------------------------------------------------------------------


class InterviewSessionCreate(CamelModel):
    difficulty: Difficulty
    question_count: int = Field(ge=1, le=20)


class InterviewSessionOut(CamelModel):
    id: str
    difficulty: Difficulty
    challenge_ids: list[str]
    time_limit_sec: int
    created_at: datetime


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class ErrorBody(CamelModel):
    code: str
    message: str


class ErrorResponse(CamelModel):
    error: ErrorBody


__all__ = [
    "Difficulty",
    "SqlTopic",
    "SubmissionStatus",
    "AchievementIcon",
    "SchemaColumn",
    "TableSchema",
    "HintOut",
    "ChallengeOut",
    "DailyChallengeOut",
    "ChallengeGenerateRequest",
    "LessonOut",
    "TrackOut",
    "SubmissionCreate",
    "SubmissionResultOut",
    "UserPublic",
    "TopicMasteryOut",
    "AchievementOut",
    "TrackProgressOut",
    "UserProgressOut",
    "InterviewSessionCreate",
    "InterviewSessionOut",
    "ErrorResponse",
]
