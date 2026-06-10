"""AI-assisted challenge generation.

The AI produces the creative parts of a challenge (title, prompt, hints,
editorial, starter SQL, chosen tables) **and a canonical solution SQL**. The
backend then *executes* that solution against the shared `sandbox` schema to
derive `expected_columns` and `expected_rows` deterministically -- so the
graded answer key is always real, never hallucinated.
"""
from __future__ import annotations

import json
import re
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.routers.submissions import _is_read_only, _normalize
from app.db import models
from app.db.sandboxes import SANDBOX_SCHEMA, sandbox_exists
from app.db.seed import SHARED_TABLES
from app.utils.config import settings

_ALLOWED_DIFFICULTIES = {"easy", "medium", "hard", "expert"}
_ALLOWED_TOPICS = {
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
}
_SLUG_RE = re.compile(r"[^a-z0-9]+")


class ChallengeGenerationError(RuntimeError):
    """Raised when generation is misconfigured or the model output is unusable."""


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------


def _schema_doc() -> str:
    """Render the shared sandbox tables + sample rows for the system prompt."""
    blocks: list[str] = []
    for table in SHARED_TABLES.values():
        cols = ", ".join(
            f"{c['name']} {c['type']}"
            + (f" ({c['note']})" if c.get("note") else "")
            for c in table["columns"]
        )
        rows = json.dumps(table.get("sampleRows", []), default=str)
        blocks.append(f"- {table['name']}({cols})\n    rows: {rows}")
    return "\n".join(blocks)


_SYSTEM_PROMPT = """You are a SQL challenge author for "SQLdle" (a Wordle-for-SQL game).
You create one self-contained PostgreSQL challenge that is solvable using ONLY
the shared sandbox tables described below. Never invent new tables or columns.

SANDBOX TABLES (this is the complete, exact seeded dataset):
{schema}

RULES:
- The solution must be a SINGLE read-only statement: SELECT or WITH ... SELECT.
  No INSERT/UPDATE/DELETE/DDL and no semicolon-separated multiple statements.
- `orders.created_at` is a TIMESTAMP. Cast with `::date` for day grouping and
  use EXTRACT(MONTH/YEAR FROM created_at) for month/year.
- The prompt MUST state the exact output column names and the row ordering, and
  the solution MUST use an explicit ORDER BY that matches that ordering.
- Difficulty must be one of: easy, medium, hard, expert.
- Topics must be chosen from: basics, filtering, joins, aggregation, subqueries,
  window-functions, ctes, indexing, performance, modeling, transactions.
- Only reference tables you list in "tables", chosen from: {table_names}.

Respond with a STRICT JSON object (no markdown, no commentary) with this shape:
{{
  "title": "string",
  "slug": "kebab-case-string",
  "difficulty": "easy|medium|hard|expert",
  "topics": ["..."],
  "tables": ["..."],
  "estimated_minutes": 8,
  "prompt": "string stating exact output columns and ordering",
  "expected_columns": ["col1", "col2"],
  "starter_sql": "optional string or null",
  "hints": ["hint 1", "hint 2"],
  "editorial": "short explanation of the approach",
  "solution_sql": "the canonical single SELECT/WITH that produces the answer"
}}
"""


def _user_prompt(req_difficulty, req_topics, req_tables, theme) -> str:
    parts: list[str] = ["Create one new challenge."]
    if req_difficulty:
        parts.append(f"Difficulty: {req_difficulty}.")
    if req_topics:
        parts.append(f"Prefer these topics: {', '.join(req_topics)}.")
    if req_tables:
        parts.append(f"Prefer using these tables: {', '.join(req_tables)}.")
    if theme:
        parts.append(f"Theme / extra guidance: {theme}")
    parts.append("Make it interesting and unambiguous.")
    return " ".join(parts)


# ---------------------------------------------------------------------------
# Model call + validation
# ---------------------------------------------------------------------------


def _call_model(user_prompt: str) -> dict[str, Any]:
    if not settings.openai_api_key:
        raise ChallengeGenerationError(
            "AI generation is not configured. Set OPENAI_API_KEY (and optionally "
            "OPENAI_BASE_URL / OPENAI_MODEL) in app/.env."
        )

    # Imported lazily so the app still boots without the dependency configured.
    from openai import OpenAI

    client = OpenAI(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url or None,
    )
    system = _SYSTEM_PROMPT.format(
        schema=_schema_doc(),
        table_names=", ".join(SHARED_TABLES.keys()),
    )
    try:
        completion = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.8,
        )
    except Exception as exc:  # noqa: BLE001
        raise ChallengeGenerationError(f"AI request failed: {exc}") from exc

    content = completion.choices[0].message.content or ""
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ChallengeGenerationError(
            "AI returned invalid JSON."
        ) from exc
    if not isinstance(data, dict):
        raise ChallengeGenerationError("AI returned a non-object JSON payload.")
    return data


def _slugify(value: str) -> str:
    return _SLUG_RE.sub("-", value.strip().lower()).strip("-") or "challenge"


def _unique(db: Session, base_slug: str) -> tuple[str, str]:
    """Return a (id, slug) pair not already present in the challenges table."""
    slug = base_slug
    n = 2
    while db.query(models.Challenge).filter(
        (models.Challenge.slug == slug) | (models.Challenge.id == f"ch-{slug}")
    ).first() is not None:
        slug = f"{base_slug}-{n}"
        n += 1
    return f"ch-{slug}", slug


def _validate(data: dict[str, Any]) -> dict[str, Any]:
    required = ["title", "prompt", "solution_sql"]
    for key in required:
        if not data.get(key) or not isinstance(data[key], str):
            raise ChallengeGenerationError(f"AI output missing required field: {key}")

    difficulty = str(data.get("difficulty", "medium")).lower()
    if difficulty not in _ALLOWED_DIFFICULTIES:
        difficulty = "medium"

    topics = [t for t in data.get("topics", []) if t in _ALLOWED_TOPICS]
    if not topics:
        topics = ["basics"]

    tables = [t for t in data.get("tables", []) if t in SHARED_TABLES]
    if not tables:
        # Fall back to every table referenced in the solution text.
        tables = [name for name in SHARED_TABLES if re.search(rf"\b{name}\b", data["solution_sql"])]
    if not tables:
        raise ChallengeGenerationError("AI did not reference any known sandbox table.")

    hints = [str(h) for h in data.get("hints", []) if str(h).strip()]
    est = data.get("estimated_minutes", 8)
    try:
        est = max(1, min(60, int(est)))
    except (TypeError, ValueError):
        est = 8

    return {
        "title": data["title"].strip(),
        "slug": _slugify(data.get("slug") or data["title"]),
        "difficulty": difficulty,
        "topics": topics,
        "tables": tables,
        "estimated_minutes": est,
        "prompt": data["prompt"].strip(),
        "starter_sql": (data.get("starter_sql") or None),
        "hints": hints,
        "editorial": str(data.get("editorial", "")).strip(),
        "solution_sql": data["solution_sql"].strip(),
    }


def _derive_answer_key(db: Session, solution_sql: str) -> tuple[list[str], list[list[Any]]]:
    """Execute the canonical SQL against the sandbox to derive the answer key."""
    if not _is_read_only(solution_sql):
        raise ChallengeGenerationError(
            "AI solution_sql must be a single read-only SELECT/WITH statement."
        )
    if not sandbox_exists(db, SANDBOX_SCHEMA):
        raise ChallengeGenerationError(
            f"Sandbox '{SANDBOX_SCHEMA}' is not built. Run `python -m app.db.sandboxes`."
        )
    try:
        db.execute(text(f'SET LOCAL search_path TO "{SANDBOX_SCHEMA}"'))
        result = db.execute(text(solution_sql))
        columns = list(result.keys())
        rows = [list(r) for r in result.fetchall()]
    except Exception as exc:  # noqa: BLE001
        raise ChallengeGenerationError(f"AI solution_sql failed to run: {exc}") from exc
    finally:
        db.rollback()  # SELECT-only; also clears SET LOCAL search_path.

    if not columns:
        raise ChallengeGenerationError("AI solution produced no columns.")
    return columns, _normalize(rows)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def generate_challenge(
    db: Session,
    *,
    difficulty: str | None = None,
    topics: list[str] | None = None,
    tables: list[str] | None = None,
    theme: str | None = None,
) -> models.Challenge:
    """Generate a challenge via the AI agent and persist it. Returns the row."""
    data = _validate(_call_model(_user_prompt(difficulty, topics, tables, theme)))

    # Derive the real answer key from the sandbox (authoritative, not the model).
    columns, rows = _derive_answer_key(db, data["solution_sql"])
    # Prefer the executed column names; fall back to model-stated names.
    expected_columns = data.get("expected_columns") or columns
    if len(expected_columns) != len(columns):
        expected_columns = columns

    challenge_id, slug = _unique(db, data["slug"])

    topic_rows = (
        db.query(models.Topic).filter(models.Topic.slug.in_(data["topics"])).all()
    )

    challenge = models.Challenge(
        id=challenge_id,
        slug=slug,
        title=data["title"],
        difficulty=models.Difficulty(data["difficulty"]),
        estimated_minutes=data["estimated_minutes"],
        prompt=data["prompt"],
        schema_tables=[SHARED_TABLES[name] for name in data["tables"]],
        expected_columns=list(expected_columns),
        expected_rows=rows,
        starter_sql=data["starter_sql"],
        editorial=data["editorial"],
    )
    challenge.topics = topic_rows
    for i, hint_text in enumerate(data["hints"]):
        challenge.hints.append(
            models.Hint(id=f"{challenge_id}-h{i + 1}", position=i, text=hint_text)
        )

    db.add(challenge)
    db.commit()
    db.refresh(challenge)
    return challenge
