"""SQLAlchemy engine, session factory, and declarative Base (PostgreSQL)."""
from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.utils.config import settings


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


engine = create_engine(
    settings.pg_connection_string,
    echo=settings.echo_sql,
    future=True,
    pool_pre_ping=True,
)


@event.listens_for(engine, "connect")
def _set_search_path(dbapi_connection, _connection_record) -> None:
    """Pin search_path on every new DBAPI connection.

    Guards against a pooled connection inheriting a stale search_path (e.g. a
    sandbox schema left by a `SET search_path`). Submissions layer a
    `SET LOCAL search_path` per transaction on top of this default.

    Note: Neon's pooled endpoint rejects libpq `options=-c search_path=...`
    startup params, so we set it post-connect here instead.
    """
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("SET search_path TO public")
    finally:
        cursor.close()


SessionLocal = sessionmaker(
    bind=engine, autocommit=False, autoflush=False, expire_on_commit=False
)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a scoped session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
