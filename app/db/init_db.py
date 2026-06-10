"""Create the database schema and seed initial content.

Run with::

    python -m app.init_db          # create tables + seed
    python -m app.init_db --drop   # drop existing tables first (destructive)
"""
from __future__ import annotations

import argparse
import sys

from app.utils.config import settings
from app.db.db import Base, SessionLocal, engine
from app.db import models  # noqa: F401  -- ensure models are registered on Base.metadata
from app.db.seed import seed_all
from app.db.sandboxes import build_sandbox


def init_db(drop: bool = False) -> None:
    if drop:
        print(f"Dropping all tables on {settings.pg_connection_string}")
        Base.metadata.drop_all(bind=engine)

    print(f"Creating tables on {settings.pg_connection_string}")
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as session:
        seed_all(session)

    print("Building shared sandbox schema...")
    build_sandbox()
    print("Database initialized.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Initialize the SQLdle database.")
    parser.add_argument(
        "--drop",
        action="store_true",
        help="Drop existing tables before creating them. Destructive.",
    )
    args = parser.parse_args(argv)
    init_db(drop=args.drop)
    return 0


if __name__ == "__main__":
    sys.exit(main())
