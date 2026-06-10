"""Shared sandbox schema.

All challenges run against ONE schema (``SANDBOX_SCHEMA``) built from
``app.db.seed.SHARED_TABLES``. Tables that appear in multiple challenges are
unified there with a superset of columns, so a single set of tables satisfies
every challenge.

Run as a script to (re)build the sandbox::

    python -m app.db.sandboxes
"""
from __future__ import annotations

import re
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.db import SessionLocal
from app.db.seed import SHARED_TABLES

# The single schema every submission is executed against.
SANDBOX_SCHEMA = "sandbox"

# Loose mapping from seed types to portable Postgres types.
_TYPE_MAP: dict[str, str] = {
    "INT": "INTEGER",
    "INTEGER": "INTEGER",
    "BIGINT": "BIGINT",
    "SMALLINT": "SMALLINT",
    "TEXT": "TEXT",
    "VARCHAR": "TEXT",
    "STRING": "TEXT",
    "NUMERIC": "NUMERIC",
    "DECIMAL": "NUMERIC",
    "REAL": "REAL",
    "FLOAT": "DOUBLE PRECISION",
    "DOUBLE": "DOUBLE PRECISION",
    "DOUBLE PRECISION": "DOUBLE PRECISION",
    "TIMESTAMP": "TIMESTAMP",
    "TIMESTAMPTZ": "TIMESTAMPTZ",
    "DATE": "DATE",
    "TIME": "TIME",
    "BOOLEAN": "BOOLEAN",
    "BOOL": "BOOLEAN",
    "JSON": "JSONB",
    "JSONB": "JSONB",
    "UUID": "UUID",
}

_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _check_ident(name: str) -> str:
    if not _IDENT_RE.match(name):
        raise ValueError(f"Unsafe SQL identifier: {name!r}")
    return name


def _map_type(raw: str) -> str:
    key = raw.strip().upper()
    return _TYPE_MAP.get(key, raw)


def sandbox_exists(db: Session, schema: str = SANDBOX_SCHEMA) -> bool:
    """True if the sandbox schema is present in the connected database."""
    return (
        db.execute(
            text("SELECT 1 FROM information_schema.schemata WHERE schema_name = :s"),
            {"s": schema},
        ).first()
        is not None
    )


def build_sandbox(db: Session | None = None) -> str:
    """Drop + recreate the shared sandbox schema and load all shared tables."""
    own_session = db is None
    if own_session:
        db = SessionLocal()
    try:
        schema = SANDBOX_SCHEMA
        db.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        db.execute(text(f'CREATE SCHEMA "{schema}"'))

        for table in SHARED_TABLES.values():
            table_name = _check_ident(table["name"])
            columns: list[dict[str, Any]] = table.get("columns", [])
            if not columns:
                continue

            col_defs: list[str] = []
            col_names: list[str] = []
            for col in columns:
                col_name = _check_ident(col["name"])
                col_type = _map_type(col["type"])
                col_defs.append(f'"{col_name}" {col_type}')
                col_names.append(col_name)

            db.execute(
                text(
                    f'CREATE TABLE "{schema}"."{table_name}" '
                    f'({", ".join(col_defs)})'
                )
            )

            sample_rows: list[dict[str, Any]] = table.get("sampleRows") or []
            if not sample_rows:
                continue

            placeholders = ", ".join(f":{n}" for n in col_names)
            quoted_cols = ", ".join(f'"{n}"' for n in col_names)
            insert_sql = text(
                f'INSERT INTO "{schema}"."{table_name}" ({quoted_cols}) '
                f"VALUES ({placeholders})"
            )
            for row in sample_rows:
                db.execute(insert_sql, {n: row.get(n) for n in col_names})

            print(f"  loaded {table_name}  ({len(sample_rows)} row(s))")

        db.commit()
        print(f"Sandbox schema '{schema}' ready with {len(SHARED_TABLES)} table(s).")
        return schema
    finally:
        if own_session:
            db.close()


def main() -> int:
    build_sandbox()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
