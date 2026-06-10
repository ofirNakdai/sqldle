"""Seed content for SQLdle.

Mirrors `src/data/mockData.ts` so the API serves the same content the
frontend's mock client returns.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

import app.db.models as m


# ---------------------------------------------------------------------------
# Topic taxonomy
# ---------------------------------------------------------------------------

TOPICS: list[tuple[str, str]] = [
    ("basics", "Basics"),
    ("filtering", "Filtering"),
    ("joins", "Joins"),
    ("aggregation", "Aggregation"),
    ("subqueries", "Subqueries"),
    ("window-functions", "Window functions"),
    ("ctes", "CTEs"),
    ("indexing", "Indexing"),
    ("performance", "Performance"),
    ("modeling", "Modeling"),
    ("transactions", "Transactions"),
]


# ---------------------------------------------------------------------------
# Shared sandbox dataset
# ---------------------------------------------------------------------------
#
# Every challenge runs against ONE shared schema. Tables that appear in
# multiple challenges (e.g. `orders`, `employees`) are unified here with a
# superset of columns, so a single set of tables satisfies all challenges.
#
# `SHARED_TABLES` is the single source of truth:
#   * `app.db.sandboxes` builds these tables (+ rows) into one schema.
#   * Each challenge's `schema_tables` is derived from these definitions for
#     the frontend "schema" panel (see `_tables(*names)` below).
#   * `expected_rows` for every challenge was computed by running its
#     canonical solution against this exact dataset.

SHARED_TABLES: dict[str, dict[str, Any]] = {
    "customers": {
        "name": "customers",
        "columns": [
            {"name": "id", "type": "INT", "note": "PK"},
            {"name": "name", "type": "TEXT"},
            {"name": "country", "type": "TEXT"},
        ],
        "sampleRows": [
            {"id": 1, "name": "Acme Corp", "country": "US"},
            {"id": 2, "name": "Globex", "country": "DE"},
            {"id": 3, "name": "Initech", "country": "US"},
            {"id": 4, "name": "Umbrella", "country": "GB"},
        ],
    },
    "orders": {
        "name": "orders",
        "columns": [
            {"name": "id", "type": "INT", "note": "PK"},
            {"name": "customer_id", "type": "INT", "note": "FK customers.id"},
            {"name": "amount", "type": "NUMERIC"},
            {"name": "created_at", "type": "TIMESTAMP", "note": "indexed"},
        ],
        "sampleRows": [
            {"id": 101, "customer_id": 1, "amount": 250, "created_at": "2025-11-01 09:00:00"},
            {"id": 102, "customer_id": 1, "amount": 50, "created_at": "2025-11-01 15:30:00"},
            {"id": 103, "customer_id": 2, "amount": 90, "created_at": "2025-11-01 11:00:00"},
            {"id": 104, "customer_id": 1, "amount": 410, "created_at": "2025-11-02 10:15:00"},
            {"id": 105, "customer_id": 3, "amount": 200, "created_at": "2025-11-02 14:00:00"},
            {"id": 106, "customer_id": 3, "amount": 120, "created_at": "2025-11-12 10:00:00"},
            {"id": 107, "customer_id": 2, "amount": 75, "created_at": "2025-11-12 16:45:00"},
            {"id": 108, "customer_id": 4, "amount": 300, "created_at": "2025-11-13 08:30:00"},
        ],
    },
    "employees": {
        "name": "employees",
        "columns": [
            {"name": "id", "type": "INT", "note": "PK"},
            {"name": "name", "type": "TEXT"},
            {"name": "salary", "type": "NUMERIC"},
            {"name": "manager_id", "type": "INT", "note": "FK employees.id"},
        ],
        "sampleRows": [
            {"id": 1, "name": "Ada", "salary": 300, "manager_id": None},
            {"id": 2, "name": "Bo", "salary": 200, "manager_id": 1},
            {"id": 3, "name": "Cy", "salary": 150, "manager_id": 2},
            {"id": 4, "name": "Di", "salary": 200, "manager_id": 1},
            {"id": 5, "name": "Eve", "salary": 100, "manager_id": 3},
        ],
    },
    "logins": {
        "name": "logins",
        "columns": [
            {"name": "user_id", "type": "INT"},
            {"name": "login_date", "type": "DATE"},
        ],
        "sampleRows": [
            {"user_id": 1, "login_date": "2025-11-01"},
            {"user_id": 1, "login_date": "2025-11-02"},
            {"user_id": 1, "login_date": "2025-11-03"},
            {"user_id": 1, "login_date": "2025-11-05"},
            {"user_id": 2, "login_date": "2025-11-01"},
            {"user_id": 2, "login_date": "2025-11-02"},
        ],
    },
}


def _tables(*names: str) -> list[dict[str, Any]]:
    """Return shared table definitions for the frontend schema panel."""
    return [SHARED_TABLES[n] for n in names]


# ---------------------------------------------------------------------------
# Challenges
# ---------------------------------------------------------------------------

CHALLENGES: list[dict[str, Any]] = [
    {
        "id": "ch-top-customers",
        "slug": "top-customers-by-revenue",
        "title": "Top customers by revenue",
        "difficulty": m.Difficulty.easy,
        "topics": ["aggregation", "joins"],
        "estimated_minutes": 8,
        "prompt": (
            "Return the top 3 customers by total order revenue. Output "
            "`customer_name` and `total_revenue` ordered by `total_revenue` "
            "descending."
        ),
        "schema_tables": _tables("customers", "orders"),
        "expected_columns": ["customer_name", "total_revenue"],
        "expected_rows": [
            ["Acme Corp", 710],
            ["Initech", 320],
            ["Umbrella", 300],
        ],
        "starter_sql": (
            "-- Join customers and orders, sum amount, return top 3.\n"
            "SELECT\n  c.name AS customer_name,\n  SUM(o.amount) AS total_revenue\n"
            "FROM customers c\nJOIN orders o ON o.customer_id = c.id\n"
            "GROUP BY c.name\nORDER BY total_revenue DESC\nLIMIT 3;"
        ),
        "hints": [
            "Join `customers` and `orders` on `customer_id`.",
            "Use `SUM(amount)` with `GROUP BY` on the customer.",
            "Order by the total descending and `LIMIT 3`.",
        ],
        "editorial": (
            "Aggregations are the bread and butter of SQL. Join the parent table "
            "to the fact table, group by the dimension you care about, and apply "
            "the aggregate. Always alias aggregates so the API/result is stable."
        ),
    },
    {
        "id": "ch-second-highest-salary",
        "slug": "second-highest-salary",
        "title": "Second highest salary",
        "difficulty": m.Difficulty.medium,
        "topics": ["window-functions", "subqueries"],
        "estimated_minutes": 12,
        "prompt": (
            "From the `employees` table, return the second highest distinct "
            "`salary`. If it does not exist, return `NULL`. Output a single "
            "column named `second_highest`."
        ),
        "schema_tables": _tables("employees"),
        "expected_columns": ["second_highest"],
        "expected_rows": [[200]],
        "starter_sql": (
            "SELECT MAX(salary) AS second_highest\n"
            "FROM employees\n"
            "WHERE salary < (SELECT MAX(salary) FROM employees);"
        ),
        "hints": [
            "Find the maximum salary first.",
            "Then find the max below that maximum.",
            "`DENSE_RANK()` is another clean approach.",
        ],
        "editorial": (
            "Two idiomatic patterns: a self-referencing subquery "
            "`MAX(salary) WHERE salary < MAX(salary)`, or "
            "`DENSE_RANK() OVER (ORDER BY salary DESC) = 2`. Both correctly "
            "handle ties and missing values."
        ),
    },
    {
        "id": "ch-running-total",
        "slug": "running-total-by-day",
        "title": "Running total by day",
        "difficulty": m.Difficulty.medium,
        "topics": ["window-functions"],
        "estimated_minutes": 15,
        "prompt": (
            "For each calendar day in `orders`, compute the running total of "
            "`amount` ordered by date. `created_at` is a `TIMESTAMP`, so cast "
            "it to a date. Output `day`, `daily_total`, `running_total`."
        ),
        "schema_tables": _tables("orders"),
        "expected_columns": ["day", "daily_total", "running_total"],
        "expected_rows": [
            ["2025-11-01", 390, 390],
            ["2025-11-02", 610, 1000],
            ["2025-11-12", 195, 1195],
            ["2025-11-13", 300, 1495],
        ],
        "starter_sql": (
            "SELECT\n  created_at::date AS day,\n  SUM(amount) AS daily_total,\n"
            "  SUM(SUM(amount)) OVER (ORDER BY created_at::date) AS running_total\n"
            "FROM orders\nGROUP BY created_at::date\nORDER BY created_at::date;"
        ),
        "hints": [
            "Aggregate by day first.",
            "A window function over the aggregate gives the running total.",
        ],
        "editorial": (
            "You can nest aggregates inside window functions: "
            "`SUM(SUM(amount)) OVER (ORDER BY day)`. This is one of the "
            "cleanest tricks once you internalize the order of operations."
        ),
    },
    {
        "id": "ch-nth-purchase",
        "slug": "first-purchase-per-customer",
        "title": "First purchase per customer",
        "difficulty": m.Difficulty.medium,
        "topics": ["window-functions", "ctes"],
        "estimated_minutes": 12,
        "prompt": (
            "Return each customer's first order: `customer_id`, `order_id`, "
            "`amount`, `created_at`. Use a window function."
        ),
        "schema_tables": _tables("orders"),
        "expected_columns": ["customer_id", "order_id", "amount", "created_at"],
        "expected_rows": [
            [1, 101, 250, "2025-11-01T09:00:00"],
            [2, 103, 90, "2025-11-01T11:00:00"],
            [3, 105, 200, "2025-11-02T14:00:00"],
            [4, 108, 300, "2025-11-13T08:30:00"],
        ],
        "starter_sql": (
            "WITH ranked AS (\n"
            "  SELECT o.*,\n"
            "         ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY created_at) AS rn\n"
            "  FROM orders o\n"
            ")\n"
            "SELECT customer_id, id AS order_id, amount, created_at\n"
            "FROM ranked\nWHERE rn = 1;"
        ),
        "hints": [
            "Partition by customer, order by date.",
            "Filter `ROW_NUMBER() = 1`.",
        ],
        "editorial": (
            "`ROW_NUMBER() OVER (PARTITION BY ... ORDER BY ...)` followed by "
            "`WHERE rn = 1` is the canonical 'first per group' pattern. Use "
            "`RANK`/`DENSE_RANK` if you need to keep ties."
        ),
    },
    {
        "id": "ch-recursive-org",
        "slug": "recursive-org-chart",
        "title": "Recursive org chart",
        "difficulty": m.Difficulty.hard,
        "topics": ["ctes"],
        "estimated_minutes": 20,
        "prompt": (
            "Given `employees(id, name, manager_id)`, return every employee "
            "with their reporting chain depth from the CEO (manager_id IS NULL). "
            "Output `id`, `name`, `depth`."
        ),
        "schema_tables": _tables("employees"),
        "expected_columns": ["id", "name", "depth"],
        "expected_rows": [
            [1, "Ada", 0],
            [2, "Bo", 1],
            [4, "Di", 1],
            [3, "Cy", 2],
            [5, "Eve", 3],
        ],
        "starter_sql": (
            "WITH RECURSIVE chain AS (\n"
            "  SELECT id, name, 0 AS depth\n"
            "  FROM employees WHERE manager_id IS NULL\n"
            "  UNION ALL\n"
            "  SELECT e.id, e.name, c.depth + 1\n"
            "  FROM employees e\n"
            "  JOIN chain c ON e.manager_id = c.id\n"
            ")\n"
            "SELECT * FROM chain ORDER BY depth, id;"
        ),
        "hints": [
            "Anchor: rows where `manager_id IS NULL`.",
            "Recursive step joins back to the CTE.",
        ],
        "editorial": (
            "Recursive CTEs have two parts joined by `UNION ALL`: an anchor "
            "and a recursive step. Always confirm a base case exists or you "
            "will hit infinite recursion."
        ),
    },
    {
        "id": "ch-gaps-and-islands",
        "slug": "gaps-and-islands",
        "title": "Gaps and islands",
        "difficulty": m.Difficulty.expert,
        "topics": ["window-functions", "ctes"],
        "estimated_minutes": 25,
        "prompt": (
            "Given a table `logins(user_id, login_date)` of distinct daily "
            "logins, find the longest consecutive-day login streak per user. "
            "Output `user_id`, `streak_length`, `streak_start`, `streak_end`."
        ),
        "schema_tables": _tables("logins"),
        "expected_columns": ["user_id", "streak_length", "streak_start", "streak_end"],
        "expected_rows": [
            [1, 3, "2025-11-01", "2025-11-03"],
            [2, 2, "2025-11-01", "2025-11-02"],
        ],
        "starter_sql": None,
        "hints": [
            "Subtract `ROW_NUMBER()` from the date to form group keys.",
            "Group by `(user_id, group_key)` and take MAX(count).",
        ],
        "editorial": (
            "The classic gaps-and-islands trick: "
            "`login_date - ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY login_date)` "
            "is constant within a consecutive run. Group by it and aggregate."
        ),
    },
    {
        "id": "ch-pivot-monthly-sales",
        "slug": "pivot-monthly-sales",
        "title": "Pivot monthly sales",
        "difficulty": m.Difficulty.hard,
        "topics": ["aggregation", "ctes"],
        "estimated_minutes": 18,
        "prompt": (
            "Pivot `orders(amount, created_at)` into one row per year with "
            "one column per month: `year`, `jan`, `feb`, ..., `dec`. Use "
            "`SUM(amount)`."
        ),
        "schema_tables": _tables("orders"),
        "expected_columns": [
            "year",
            "jan", "feb", "mar", "apr", "may", "jun",
            "jul", "aug", "sep", "oct", "nov", "dec",
        ],
        "expected_rows": [[2025, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1495, 0]],
        "starter_sql": None,
        "hints": [
            "Use `SUM(CASE WHEN month = X THEN amount ELSE 0 END)` per month.",
        ],
        "editorial": (
            "Conditional aggregation `SUM(CASE WHEN ... THEN ... END)` is the "
            "most portable way to pivot in standard SQL."
        ),
    },
    {
        "id": "ch-index-friendly",
        "slug": "index-friendly-where",
        "title": "Make this WHERE index-friendly",
        "difficulty": m.Difficulty.hard,
        "topics": ["performance", "indexing"],
        "estimated_minutes": 10,
        "prompt": (
            "The query `SELECT * FROM orders WHERE DATE(created_at) = '2025-11-12'` "
            "is slow even with an index on `created_at`. Rewrite the WHERE clause "
            "so an index on `created_at` can be used."
        ),
        "schema_tables": _tables("orders"),
        "expected_columns": ["id", "created_at"],
        "expected_rows": [
            [106, "2025-11-12T10:00:00"],
            [107, "2025-11-12T16:45:00"],
        ],
        "starter_sql": (
            "SELECT id, created_at\nFROM orders\n"
            "WHERE created_at >= '2025-11-12'\n  AND created_at <  '2025-11-13';"
        ),
        "hints": [
            "Avoid wrapping the indexed column in a function.",
            "Use a half-open range: >= start AND < next day.",
        ],
        "editorial": (
            "Wrapping an indexed column in a function (`DATE(col)`, `LOWER(col)`) "
            "usually disables the index. Rewrite predicates as sargable range "
            "scans whenever possible."
        ),
    },
]


# ---------------------------------------------------------------------------
# Tracks
# ---------------------------------------------------------------------------

TRACKS: list[dict[str, Any]] = [
    {
        "id": "tr-foundations",
        "slug": "foundations",
        "title": "SQL Foundations",
        "tagline": "From SELECT to confident joins",
        "description": (
            "Build the muscle memory for everyday SQL: filtering, sorting, "
            "joins, and aggregations."
        ),
        "difficulty": m.Difficulty.easy,
        "topics": ["basics", "filtering", "joins", "aggregation"],
        "lessons": [
            {
                "id": "ls-aggregation",
                "title": "Aggregation patterns",
                "summary": "GROUP BY, HAVING, and the canonical Top-N per group.",
                "topics": ["aggregation", "joins"],
                "challenge_ids": ["ch-top-customers"],
            }
        ],
    },
    {
        "id": "tr-windows",
        "slug": "window-functions",
        "title": "Window Functions Mastery",
        "tagline": "Think in partitions and frames",
        "description": (
            "Window functions unlock analytics SQL. Learn ROW_NUMBER, RANK, "
            "running totals, and frames."
        ),
        "difficulty": m.Difficulty.medium,
        "topics": ["window-functions", "ctes"],
        "lessons": [
            {
                "id": "ls-ranking",
                "title": "Ranking and first-per-group",
                "summary": "ROW_NUMBER, RANK, and the WHERE rn = 1 pattern.",
                "topics": ["window-functions"],
                "challenge_ids": ["ch-second-highest-salary", "ch-nth-purchase"],
            },
            {
                "id": "ls-running",
                "title": "Running totals and moving averages",
                "summary": "Frames, ORDER BY in OVER, and nested aggregates.",
                "topics": ["window-functions"],
                "challenge_ids": ["ch-running-total"],
            },
        ],
    },
    {
        "id": "tr-advanced",
        "slug": "advanced-sql",
        "title": "Advanced SQL",
        "tagline": "CTEs, recursion, and gnarly analytics",
        "description": (
            "Recursive CTEs, pivoting, and the famous gaps-and-islands. The "
            "patterns expert engineers reach for."
        ),
        "difficulty": m.Difficulty.hard,
        "topics": ["ctes", "window-functions"],
        "lessons": [
            {
                "id": "ls-recursion",
                "title": "Recursive CTEs",
                "summary": "Anchor + recursive step. Org charts, graph traversal.",
                "topics": ["ctes"],
                "challenge_ids": ["ch-recursive-org"],
            },
            {
                "id": "ls-gaps",
                "title": "Gaps and islands",
                "summary": "The trick every SQL interviewer loves.",
                "topics": ["window-functions", "ctes"],
                "challenge_ids": ["ch-gaps-and-islands"],
            },
            {
                "id": "ls-pivot",
                "title": "Pivoting with conditional aggregates",
                "summary": "Portable pivots with SUM(CASE WHEN ...).",
                "topics": ["aggregation"],
                "challenge_ids": ["ch-pivot-monthly-sales"],
            },
        ],
    },
    {
        "id": "tr-perf",
        "slug": "performance-and-indexing",
        "title": "Performance & Indexing",
        "tagline": "Make queries fast on real data",
        "description": (
            "Sargable predicates, index design, and the EXPLAIN mindset. "
            "Stop fighting the planner."
        ),
        "difficulty": m.Difficulty.hard,
        "topics": ["performance", "indexing"],
        "lessons": [
            {
                "id": "ls-sargable",
                "title": "Sargable predicates",
                "summary": "Why DATE(col) = ... destroys your index.",
                "topics": ["performance", "indexing"],
                "challenge_ids": ["ch-index-friendly"],
            }
        ],
    },
    {
        "id": "tr-interview",
        "slug": "interview-prep",
        "title": "Interview Prep",
        "tagline": "The questions you will actually be asked",
        "description": (
            "A curated set of FAANG-grade SQL interview problems with timed "
            "practice."
        ),
        "difficulty": m.Difficulty.expert,
        "topics": ["window-functions", "ctes", "aggregation", "performance"],
        "lessons": [
            {
                "id": "ls-classics",
                "title": "The classics",
                "summary": "Second highest, top-N per group, running totals.",
                "topics": ["window-functions"],
                "challenge_ids": [
                    "ch-second-highest-salary",
                    "ch-nth-purchase",
                    "ch-running-total",
                ],
            },
            {
                "id": "ls-hard",
                "title": "Hard mode",
                "summary": "Recursion, pivots, gaps and islands.",
                "topics": ["ctes", "window-functions"],
                "challenge_ids": [
                    "ch-recursive-org",
                    "ch-pivot-monthly-sales",
                    "ch-gaps-and-islands",
                ],
            },
        ],
    },
]


# ---------------------------------------------------------------------------
# Achievements catalog
# ---------------------------------------------------------------------------

ACHIEVEMENTS: list[dict[str, Any]] = [
    {
        "id": "first-solve",
        "title": "First Blood",
        "description": "Solve your first challenge.",
        "icon": m.AchievementIcon.zap,
    },
    {
        "id": "streak-7",
        "title": "On Fire",
        "description": "Maintain a 7-day streak.",
        "icon": m.AchievementIcon.flame,
    },
    {
        "id": "window-master",
        "title": "Window Master",
        "description": "Solve every window-function challenge.",
        "icon": m.AchievementIcon.crown,
    },
    {
        "id": "perf-pro",
        "title": "Performance Pro",
        "description": "Complete the Performance & Indexing track.",
        "icon": m.AchievementIcon.trophy,
    },
]


# ---------------------------------------------------------------------------
# Demo user (created fresh, with no progress)
# ---------------------------------------------------------------------------

# Fresh user: no progress, as if the site is being run for the first time.
# Achievements, topic mastery, track progress and submissions are all earned
# at runtime by playing, so none are seeded here.
DEMO_USER: dict[str, Any] = {
    "id": "u1",
    "display_name": "You",
    "avatar_color": "#7c5cff",
    "email": "demo@sqldle.local",
    "xp": 0,
    "level": 1,
    "total_solved": 0,
    "current_streak": 0,
    "best_streak": 0,
}


# ---------------------------------------------------------------------------
# Seeding entry point
# ---------------------------------------------------------------------------


def seed_all(session: Session) -> None:
    """Populate every reference table. Idempotent: skips if already seeded."""

    if session.query(m.Challenge).first() is not None:
        return

    # Topics
    topics_by_slug: dict[str, m.Topic] = {}
    for slug, label in TOPICS:
        topic = m.Topic(slug=slug, label=label)
        session.add(topic)
        topics_by_slug[slug] = topic
    session.flush()

    # Challenges + hints + challenge<->topic
    for c in CHALLENGES:
        challenge = m.Challenge(
            id=c["id"],
            slug=c["slug"],
            title=c["title"],
            difficulty=c["difficulty"],
            estimated_minutes=c["estimated_minutes"],
            prompt=c["prompt"],
            schema_tables=c["schema_tables"],
            expected_columns=c["expected_columns"],
            expected_rows=c["expected_rows"],
            starter_sql=c.get("starter_sql"),
            editorial=c["editorial"],
        )
        challenge.topics = [topics_by_slug[t] for t in c["topics"]]
        for i, text in enumerate(c["hints"]):
            challenge.hints.append(
                m.Hint(id=f"{c['id']}-h{i + 1}", position=i, text=text)
            )
        session.add(challenge)
    session.flush()

    # Tracks + lessons + lesson<->challenge ordering
    for t in TRACKS:
        track = m.Track(
            id=t["id"],
            slug=t["slug"],
            title=t["title"],
            tagline=t["tagline"],
            description=t["description"],
            difficulty=t["difficulty"],
        )
        track.topics = [topics_by_slug[s] for s in t["topics"]]
        for li, lesson_def in enumerate(t["lessons"]):
            lesson = m.Lesson(
                id=lesson_def["id"],
                position=li,
                title=lesson_def["title"],
                summary=lesson_def["summary"],
            )
            lesson.topics = [topics_by_slug[s] for s in lesson_def["topics"]]
            for ci, challenge_id in enumerate(lesson_def["challenge_ids"]):
                lesson.challenges.append(
                    m.LessonChallenge(
                        challenge_id=challenge_id,
                        position=ci,
                    )
                )
            track.lessons.append(lesson)
        session.add(track)
    session.flush()

    # Daily challenges: yesterday, today, tomorrow point at sensible picks.
    today = date.today()
    daily_plan = [
        (today - timedelta(days=1), "ch-top-customers"),
        (today, "ch-running-total"),
        (today + timedelta(days=1), "ch-nth-purchase"),
    ]
    for day, cid in daily_plan:
        session.add(m.DailyChallenge(day=day, challenge_id=cid))

    # Achievements catalog
    for a in ACHIEVEMENTS:
        session.add(
            m.Achievement(
                id=a["id"], title=a["title"], description=a["description"], icon=a["icon"]
            )
        )

    # Demo user (fresh start: no submissions, achievements, mastery or progress)
    user = m.User(
        id=DEMO_USER["id"],
        email=DEMO_USER["email"],
        display_name=DEMO_USER["display_name"],
        avatar_color=DEMO_USER["avatar_color"],
        xp=DEMO_USER["xp"],
        level=DEMO_USER["level"],
        total_solved=DEMO_USER["total_solved"],
        current_streak=DEMO_USER["current_streak"],
        best_streak=DEMO_USER["best_streak"],
        last_activity_day=None,
    )
    session.add(user)

    session.commit()


__all__ = ["seed_all"]
