"""SQLAlchemy ORM models for SQLdle (PostgreSQL).

Nested or free-shape data (challenge table samples, expected rows) is stored
in PostgreSQL `JSONB` columns for efficient querying and indexing.
"""
from __future__ import annotations

import enum
from datetime import datetime, date
from typing import Any

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.db import Base


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class Difficulty(str, enum.Enum):
    easy = "easy"
    medium = "medium"
    hard = "hard"
    expert = "expert"


class SubmissionStatus(str, enum.Enum):
    pass_ = "pass"  # `pass` is a reserved word
    fail = "fail"
    error = "error"


class AchievementIcon(str, enum.Enum):
    flame = "flame"
    trophy = "trophy"
    target = "target"
    zap = "zap"
    crown = "crown"


# ---------------------------------------------------------------------------
# Topics (lookup table + association tables)
# ---------------------------------------------------------------------------


class Topic(Base):
    """SQL topic taxonomy. Slug matches the `SqlTopic` union on the frontend."""

    __tablename__ = "topics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    label: Mapped[str] = mapped_column(String(128), nullable=False)


class ChallengeTopic(Base):
    __tablename__ = "challenge_topics"

    challenge_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("challenges.id", ondelete="CASCADE"), primary_key=True
    )
    topic_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("topics.id", ondelete="CASCADE"), primary_key=True
    )


class TrackTopic(Base):
    __tablename__ = "track_topics"

    track_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("tracks.id", ondelete="CASCADE"), primary_key=True
    )
    topic_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("topics.id", ondelete="CASCADE"), primary_key=True
    )


class LessonTopic(Base):
    __tablename__ = "lesson_topics"

    lesson_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("lessons.id", ondelete="CASCADE"), primary_key=True
    )
    topic_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("topics.id", ondelete="CASCADE"), primary_key=True
    )


# ---------------------------------------------------------------------------
# Challenges
# ---------------------------------------------------------------------------


class Challenge(Base):
    """A single SQL practice problem."""

    __tablename__ = "challenges"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    slug: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    difficulty: Mapped[Difficulty] = mapped_column(
        Enum(Difficulty, name="difficulty"), nullable=False
    )
    estimated_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=10)

    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    editorial: Mapped[str] = mapped_column(Text, nullable=False, default="")
    starter_sql: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Nested, free-shape: list of {name, columns[], sampleRows[]}
    schema_tables: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    # Expected result set
    expected_columns: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    expected_rows: Mapped[list[list[Any]]] = mapped_column(
        JSONB, nullable=False, default=list
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    topics: Mapped[list[Topic]] = relationship(
        Topic,
        secondary="challenge_topics",
        order_by=Topic.slug,
        lazy="selectin",
    )
    hints: Mapped[list["Hint"]] = relationship(
        "Hint",
        back_populates="challenge",
        cascade="all, delete-orphan",
        order_by="Hint.position",
        lazy="selectin",
    )


class Hint(Base):
    """Ordered hint attached to a challenge."""

    __tablename__ = "hints"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    challenge_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("challenges.id", ondelete="CASCADE"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    text: Mapped[str] = mapped_column(Text, nullable=False)

    challenge: Mapped[Challenge] = relationship(Challenge, back_populates="hints")

    __table_args__ = (
        Index("ix_hints_challenge_position", "challenge_id", "position"),
    )


# ---------------------------------------------------------------------------
# Tracks & lessons
# ---------------------------------------------------------------------------


class Track(Base):
    __tablename__ = "tracks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    slug: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    tagline: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    difficulty: Mapped[Difficulty] = mapped_column(
        Enum(Difficulty, name="difficulty"), nullable=False
    )

    topics: Mapped[list[Topic]] = relationship(
        Topic,
        secondary="track_topics",
        order_by=Topic.slug,
        lazy="selectin",
    )
    lessons: Mapped[list["Lesson"]] = relationship(
        "Lesson",
        back_populates="track",
        cascade="all, delete-orphan",
        order_by="Lesson.position",
        lazy="selectin",
    )


class Lesson(Base):
    __tablename__ = "lessons"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    track_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("tracks.id", ondelete="CASCADE"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")

    track: Mapped[Track] = relationship(Track, back_populates="lessons")
    topics: Mapped[list[Topic]] = relationship(
        Topic,
        secondary="lesson_topics",
        order_by=Topic.slug,
        lazy="selectin",
    )
    challenges: Mapped[list["LessonChallenge"]] = relationship(
        "LessonChallenge",
        back_populates="lesson",
        cascade="all, delete-orphan",
        order_by="LessonChallenge.position",
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_lessons_track_position", "track_id", "position"),
    )


class LessonChallenge(Base):
    """Ordered membership: a challenge inside a lesson."""

    __tablename__ = "lesson_challenges"

    lesson_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("lessons.id", ondelete="CASCADE"), primary_key=True
    )
    challenge_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("challenges.id", ondelete="CASCADE"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    lesson: Mapped[Lesson] = relationship(Lesson, back_populates="challenges")
    challenge: Mapped[Challenge] = relationship(Challenge, lazy="joined")


# ---------------------------------------------------------------------------
# Daily challenge
# ---------------------------------------------------------------------------


class DailyChallenge(Base):
    """One row per calendar day pointing at a challenge."""

    __tablename__ = "daily_challenges"

    day: Mapped[date] = mapped_column(Date, primary_key=True)
    challenge_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("challenges.id", ondelete="RESTRICT"), nullable=False
    )

    challenge: Mapped[Challenge] = relationship(Challenge, lazy="joined")


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    email: Mapped[str | None] = mapped_column(String(256), unique=True, nullable=True)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    avatar_color: Mapped[str] = mapped_column(String(16), nullable=False, default="#7c5cff")
    password_hash: Mapped[str | None] = mapped_column(String(256), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    xp: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    level: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    total_solved: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    current_streak: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    best_streak: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_activity_day: Mapped[date | None] = mapped_column(Date, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


# ---------------------------------------------------------------------------
# Submissions
# ---------------------------------------------------------------------------


class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    challenge_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("challenges.id", ondelete="CASCADE"), nullable=False
    )

    sql: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[SubmissionStatus] = mapped_column(
        Enum(SubmissionStatus, name="submission_status"), nullable=False
    )
    message: Mapped[str] = mapped_column(Text, nullable=False, default="")
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    columns: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    rows_returned: Mapped[list[list[Any]] | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_submissions_user_created", "user_id", "created_at"),
        Index("ix_submissions_user_challenge", "user_id", "challenge_id"),
    )


# ---------------------------------------------------------------------------
# Achievements
# ---------------------------------------------------------------------------


class Achievement(Base):
    """Catalog of achievable badges."""

    __tablename__ = "achievements"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    icon: Mapped[AchievementIcon] = mapped_column(
        Enum(AchievementIcon, name="achievement_icon"), nullable=False
    )


class UserAchievement(Base):
    __tablename__ = "user_achievements"

    user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    achievement_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("achievements.id", ondelete="CASCADE"), primary_key=True
    )
    unlocked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


# ---------------------------------------------------------------------------
# Mastery & track progress
# ---------------------------------------------------------------------------


class TopicMastery(Base):
    """Per-user mastery score for a topic, in [0, 1]."""

    __tablename__ = "topic_mastery"

    user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    topic_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("topics.id", ondelete="CASCADE"), primary_key=True
    )
    mastery: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    topic: Mapped[Topic] = relationship(Topic, lazy="joined")


class TrackProgress(Base):
    """Aggregate progress per (user, track)."""

    __tablename__ = "track_progress"

    user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    track_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("tracks.id", ondelete="CASCADE"), primary_key=True
    )
    completed_lessons: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_lessons: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


# ---------------------------------------------------------------------------
# Interview sessions
# ---------------------------------------------------------------------------


class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    difficulty: Mapped[Difficulty] = mapped_column(
        Enum(Difficulty, name="difficulty"), nullable=False
    )
    time_limit_sec: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    questions: Mapped[list["InterviewQuestion"]] = relationship(
        "InterviewQuestion",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="InterviewQuestion.position",
        lazy="selectin",
    )


class InterviewQuestion(Base):
    """Ordered question slot inside an interview session."""

    __tablename__ = "interview_questions"

    session_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        primary_key=True,
    )
    position: Mapped[int] = mapped_column(Integer, primary_key=True)
    challenge_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("challenges.id", ondelete="RESTRICT"), nullable=False
    )
    submission_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("submissions.id", ondelete="SET NULL"), nullable=True
    )

    session: Mapped[InterviewSession] = relationship(
        InterviewSession, back_populates="questions"
    )
    challenge: Mapped[Challenge] = relationship(Challenge, lazy="joined")


__all__ = [
    "Difficulty",
    "SubmissionStatus",
    "AchievementIcon",
    "Topic",
    "ChallengeTopic",
    "TrackTopic",
    "LessonTopic",
    "Challenge",
    "Hint",
    "Track",
    "Lesson",
    "LessonChallenge",
    "DailyChallenge",
    "User",
    "Submission",
    "Achievement",
    "UserAchievement",
    "TopicMastery",
    "TrackProgress",
    "InterviewSession",
    "InterviewQuestion",
]
