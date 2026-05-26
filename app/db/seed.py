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
        "schema_tables": [
            {
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
                ],
            },
            {
                "name": "orders",
                "columns": [
                    {"name": "id", "type": "INT", "note": "PK"},
                    {"name": "customer_id", "type": "INT", "note": "FK customers.id"},
                    {"name": "amount", "type": "NUMERIC"},
                    {"name": "created_at", "type": "TIMESTAMP"},
                ],
                "sampleRows": [
                    {"id": 101, "customer_id": 1, "amount": 250.0, "created_at": "2025-11-02"},
                    {"id": 102, "customer_id": 2, "amount": 90.0, "created_at": "2025-11-04"},
                    {"id": 103, "customer_id": 1, "amount": 410.0, "created_at": "2025-11-09"},
                ],
            },
        ],
        "expected_columns": ["customer_name", "total_revenue"],
        "expected_rows": [
            ["Acme Corp", 660],
            ["Initech", 320],
            ["Globex", 90],
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
        "schema_tables": [
            {
                "name": "employees",
                "columns": [
                    {"name": "id", "type": "INT"},
                    {"name": "name", "type": "TEXT"},
                    {"name": "salary", "type": "NUMERIC"},
                ],
                "sampleRows": [
                    {"id": 1, "name": "A", "salary": 100},
                    {"id": 2, "name": "B", "salary": 200},
                    {"id": 3, "name": "C", "salary": 300},
                ],
            }
        ],
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
            "For each day in `orders`, compute the running total of `amount` "
            "ordered by date. Output `day`, `daily_total`, `running_total`."
        ),
        "schema_tables": [
            {
                "name": "orders",
                "columns": [
                    {"name": "id", "type": "INT"},
                    {"name": "amount", "type": "NUMERIC"},
                    {"name": "created_at", "type": "DATE"},
                ],
                "sampleRows": [
                    {"id": 1, "amount": 100, "created_at": "2025-11-01"},
                    {"id": 2, "amount": 50, "created_at": "2025-11-01"},
                    {"id": 3, "amount": 200, "created_at": "2025-11-02"},
                ],
            }
        ],
        "expected_columns": ["day", "daily_total", "running_total"],
        "expected_rows": [
            ["2025-11-01", 150, 150],
            ["2025-11-02", 200, 350],
        ],
        "starter_sql": (
            "SELECT\n  created_at AS day,\n  SUM(amount) AS daily_total,\n"
            "  SUM(SUM(amount)) OVER (ORDER BY created_at) AS running_total\n"
            "FROM orders\nGROUP BY created_at\nORDER BY created_at;"
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
        "schema_tables": [
            {
                "name": "orders",
                "columns": [
                    {"name": "id", "type": "INT"},
                    {"name": "customer_id", "type": "INT"},
                    {"name": "amount", "type": "NUMERIC"},
                    {"name": "created_at", "type": "TIMESTAMP"},
                ],
                "sampleRows": [
                    {"id": 1, "customer_id": 1, "amount": 50, "created_at": "2025-10-01"},
                    {"id": 2, "customer_id": 1, "amount": 70, "created_at": "2025-10-09"},
                    {"id": 3, "customer_id": 2, "amount": 30, "created_at": "2025-10-05"},
                ],
            }
        ],
        "expected_columns": ["customer_id", "order_id", "amount", "created_at"],
        "expected_rows": [
            [1, 1, 50, "2025-10-01"],
            [2, 3, 30, "2025-10-05"],
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
        "schema_tables": [
            {
                "name": "employees",
                "columns": [
                    {"name": "id", "type": "INT"},
                    {"name": "name", "type": "TEXT"},
                    {"name": "manager_id", "type": "INT"},
                ],
                "sampleRows": [
                    {"id": 1, "name": "Ada", "manager_id": None},
                    {"id": 2, "name": "Bo", "manager_id": 1},
                    {"id": 3, "name": "Cy", "manager_id": 2},
                ],
            }
        ],
        "expected_columns": ["id", "name", "depth"],
        "expected_rows": [
            [1, "Ada", 0],
            [2, "Bo", 1],
            [3, "Cy", 2],
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
        "schema_tables": [
            {
                "name": "logins",
                "columns": [
                    {"name": "user_id", "type": "INT"},
                    {"name": "login_date", "type": "DATE"},
                ],
                "sampleRows": [
                    {"user_id": 1, "login_date": "2025-11-01"},
                    {"user_id": 1, "login_date": "2025-11-02"},
                    {"user_id": 1, "login_date": "2025-11-04"},
                ],
            }
        ],
        "expected_columns": ["user_id", "streak_length", "streak_start", "streak_end"],
        "expected_rows": [[1, 2, "2025-11-01", "2025-11-02"]],
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
        "schema_tables": [
            {
                "name": "orders",
                "columns": [
                    {"name": "amount", "type": "NUMERIC"},
                    {"name": "created_at", "type": "DATE"},
                ],
                "sampleRows": [{"amount": 100, "created_at": "2025-01-15"}],
            }
        ],
        "expected_columns": [
            "year",
            "jan", "feb", "mar", "apr", "may", "jun",
            "jul", "aug", "sep", "oct", "nov", "dec",
        ],
        "expected_rows": [[2025, 100, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]],
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
        "schema_tables": [
            {
                "name": "orders",
                "columns": [
                    {"name": "id", "type": "INT"},
                    {"name": "created_at", "type": "TIMESTAMP", "note": "indexed"},
                ],
                "sampleRows": [{"id": 1, "created_at": "2025-11-12 10:00:00"}],
            }
        ],
        "expected_columns": ["id", "created_at"],
        "expected_rows": [[1, "2025-11-12 10:00:00"]],
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
# Demo user + progress (mirrors `userProgress` in the frontend mock)
# ---------------------------------------------------------------------------

DEMO_USER: dict[str, Any] = {
    "id": "u1",
    "display_name": "You",
    "avatar_color": "#7c5cff",
    "email": "demo@sqldle.local",
    "xp": 1480,
    "level": 4,
    "total_solved": 14,
    "current_streak": 6,
    "best_streak": 11,
}

TOPIC_MASTERY: list[tuple[str, float]] = [
    ("basics", 0.95),
    ("filtering", 0.90),
    ("joins", 0.78),
    ("aggregation", 0.72),
    ("subqueries", 0.55),
    ("window-functions", 0.48),
    ("ctes", 0.32),
    ("performance", 0.25),
    ("indexing", 0.20),
]

USER_ACHIEVEMENTS: list[tuple[str, datetime]] = [
    ("first-solve", datetime(2026, 4, 30, tzinfo=timezone.utc)),
    ("streak-7", datetime(2026, 5, 12, tzinfo=timezone.utc)),
]

# Recent submissions for the demo user.
RECENT_SUBMISSIONS: list[dict[str, Any]] = [
    {
        "id": "s1",
        "challenge_id": "ch-top-customers",
        "status": m.SubmissionStatus.pass_,
        "message": "All test cases passed.",
        "duration_ms": 124,
        "created_at": datetime(2026, 5, 20, 18, 42, tzinfo=timezone.utc),
        "sql": "SELECT c.name, SUM(o.amount) FROM customers c JOIN orders o ON o.customer_id = c.id GROUP BY c.name ORDER BY 2 DESC LIMIT 3;",
    },
    {
        "id": "s2",
        "challenge_id": "ch-second-highest-salary",
        "status": m.SubmissionStatus.fail,
        "message": "Returned 1 row, expected 1 row but values differ.",
        "duration_ms": 88,
        "created_at": datetime(2026, 5, 20, 17, 11, tzinfo=timezone.utc),
        "sql": "SELECT MAX(salary) FROM employees;",
    },
    {
        "id": "s3",
        "challenge_id": "ch-running-total",
        "status": m.SubmissionStatus.pass_,
        "message": "All test cases passed.",
        "duration_ms": 162,
        "created_at": datetime(2026, 5, 19, 20, 2, tzinfo=timezone.utc),
        "sql": "SELECT created_at, SUM(amount), SUM(SUM(amount)) OVER (ORDER BY created_at) FROM orders GROUP BY created_at;",
    },
]


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

    # Demo user
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
        last_activity_day=today,
    )
    session.add(user)
    session.flush()

    # User achievements
    for ach_id, unlocked_at in USER_ACHIEVEMENTS:
        session.add(
            m.UserAchievement(
                user_id=user.id, achievement_id=ach_id, unlocked_at=unlocked_at
            )
        )

    # Topic mastery
    for slug, mastery in TOPIC_MASTERY:
        session.add(
            m.TopicMastery(
                user_id=user.id, topic_id=topics_by_slug[slug].id, mastery=mastery
            )
        )

    # Track progress (precomputed; real app would recalculate from submissions)
    track_progress = {
        "tr-foundations": (1, 1),
        "tr-windows": (2, 3),
        "tr-advanced": (0, 3),
        "tr-perf": (0, 1),
        "tr-interview": (1, 6),
    }
    for tid, (done, total) in track_progress.items():
        session.add(
            m.TrackProgress(
                user_id=user.id,
                track_id=tid,
                completed_lessons=done,
                total_lessons=total,
            )
        )

    # Recent submissions
    for s in RECENT_SUBMISSIONS:
        session.add(
            m.Submission(
                id=s["id"],
                user_id=user.id,
                challenge_id=s["challenge_id"],
                sql=s["sql"],
                status=s["status"],
                message=s["message"],
                duration_ms=s["duration_ms"],
                created_at=s["created_at"],
            )
        )

    session.commit()


__all__ = ["seed_all"]
