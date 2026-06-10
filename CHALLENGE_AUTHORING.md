# SQLdle — Challenge Authoring Guide

Everything an agent needs to generate a new SQLdle challenge: the shared
sandbox schema, the challenge data shape, the grading rules, and a
step‑by‑step recipe.

---

## 1. How the sandbox works

- **One schema for everything.** Every challenge is graded against a single
  Postgres schema named **`sandbox`**, built from a single source of truth:
  the `SHARED_TABLES` dict in [app/db/seed.py](app/db/seed.py).
- **Tables are a superset.** If a table (e.g. `orders`) is used by multiple
  challenges, its columns are the union of everything every challenge needs.
  **Do not invent per‑challenge tables.** Reuse the shared tables, or extend a
  shared table with a new (nullable‑friendly) column if absolutely required.
- **Submissions are read‑only.** User SQL runs inside a transaction with
  `SET LOCAL search_path TO "sandbox"` and is **always rolled back**. Only a
  single `SELECT` / `WITH … SELECT` statement is allowed (see §4).
- **Rebuild after data changes.** Any time you change `SHARED_TABLES`, rebuild
  the schema:

  ```powershell
  . .\venv\Scripts\Activate.ps1
  python -m app.db.sandboxes      # rebuild sandbox only
  # or a full reset (drops tables, reseeds, rebuilds sandbox):
  python -m app.db.init_db --drop
  ```

---

## 2. Sandbox tables (the only tables you may query)

All sample data below is the **exact** seeded dataset. Your challenge's
`expected_rows` must be computed against this data.

### `customers`

| column  | type | notes |
| ------- | ---- | ----- |
| id      | INT  | PK    |
| name    | TEXT |       |
| country | TEXT |       |

| id  | name      | country |
| --- | --------- | ------- |
| 1   | Acme Corp | US      |
| 2   | Globex    | DE      |
| 3   | Initech   | US      |
| 4   | Umbrella  | GB      |

### `orders`

| column      | type      | notes                                              |
| ----------- | --------- | -------------------------------------------------- |
| id          | INT       | PK                                                 |
| customer_id | INT       | FK → customers.id                                  |
| amount      | NUMERIC   |                                                    |
| created_at  | TIMESTAMP | indexed — note this is a **timestamp**, not a date |

| id  | customer_id | amount | created_at          |
| --- | ----------- | ------ | ------------------- |
| 101 | 1           | 250    | 2025-11-01 09:00:00 |
| 102 | 1           | 50     | 2025-11-01 15:30:00 |
| 103 | 2           | 90     | 2025-11-01 11:00:00 |
| 104 | 1           | 410    | 2025-11-02 10:15:00 |
| 105 | 3           | 200    | 2025-11-02 14:00:00 |
| 106 | 3           | 120    | 2025-11-12 10:00:00 |
| 107 | 2           | 75     | 2025-11-12 16:45:00 |
| 108 | 4           | 300    | 2025-11-13 08:30:00 |

### `employees`

| column     | type    | notes                                                 |
| ---------- | ------- | ----------------------------------------------------- |
| id         | INT     | PK                                                    |
| name       | TEXT    |                                                       |
| salary     | NUMERIC |                                                       |
| manager_id | INT     | FK → employees.id (self‑reference; NULL = top of org) |

| id  | name | salary | manager_id |
| --- | ---- | ------ | ---------- |
| 1   | Ada  | 300    | NULL       |
| 2   | Bo   | 200    | 1          |
| 3   | Cy   | 150    | 2          |
| 4   | Di   | 200    | 1          |
| 5   | Eve  | 100    | 3          |

### `logins`

| column     | type | notes |
| ---------- | ---- | ----- |
| user_id    | INT  |       |
| login_date | DATE |       |

| user_id | login_date |
| ------- | ---------- |
| 1       | 2025-11-01 |
| 1       | 2025-11-02 |
| 1       | 2025-11-03 |
| 1       | 2025-11-05 |
| 2       | 2025-11-01 |
| 2       | 2025-11-02 |

> **Supported column types** (mapped to Postgres in
> [app/db/sandboxes.py](app/db/sandboxes.py)): `INT`/`INTEGER`, `BIGINT`,
> `SMALLINT`, `TEXT`/`VARCHAR`/`STRING`, `NUMERIC`/`DECIMAL`, `REAL`,
> `FLOAT`/`DOUBLE`, `TIMESTAMP`, `TIMESTAMPTZ`, `DATE`, `TIME`, `BOOLEAN`,
> `JSON`/`JSONB`, `UUID`. Identifiers must match `^[A-Za-z_][A-Za-z0-9_]*$`.

---

## 3. The challenge data shape

Challenges are Python dicts in the `CHALLENGES` list in
[app/db/seed.py](app/db/seed.py). Required fields:

| field               | type           | description                                                             |
| ------------------- | -------------- | ----------------------------------------------------------------------- |
| `id`                | str            | Stable unique id, prefix `ch-` (e.g. `"ch-top-customers"`).             |
| `slug`              | str            | URL slug, kebab‑case (e.g. `"top-customers-by-revenue"`).               |
| `title`             | str            | Human title.                                                            |
| `difficulty`        | `m.Difficulty` | `easy` \| `medium` \| `hard` \| `expert`.                               |
| `topics`            | list[str]      | One or more topic slugs (see list below).                               |
| `estimated_minutes` | int            | Rough solve time.                                                       |
| `prompt`            | str            | The problem statement. State the **exact output columns and ordering**. |
| `schema_tables`     | list[dict]     | Use `_tables("customers", "orders", …)` — never hand‑write.             |
| `expected_columns`  | list[str]      | Output column names, in order (compared case‑insensitively).            |
| `expected_rows`     | list[list]     | The correct result set (see §4 for exact format).                       |
| `starter_sql`       | str \| None    | Optional editor seed. `None` for hard/expert.                           |
| `hints`             | list[str]      | Progressive hints (become `Hint` rows).                                 |
| `editorial`         | str            | Explanation shown after solving.                                        |

**Topic slugs:** `basics`, `filtering`, `joins`, `aggregation`, `subqueries`,
`window-functions`, `ctes`, `indexing`, `performance`, `modeling`,
`transactions`.

### Minimal example

```python
{
    "id": "ch-orders-per-country",
    "slug": "orders-per-country",
    "title": "Orders per country",
    "difficulty": m.Difficulty.easy,
    "topics": ["joins", "aggregation"],
    "estimated_minutes": 6,
    "prompt": (
        "Count the number of orders placed by customers in each country. "
        "Output `country` and `order_count`, ordered by `order_count` "
        "descending then `country` ascending."
    ),
    "schema_tables": _tables("customers", "orders"),
    "expected_columns": ["country", "order_count"],
    "expected_rows": [
        ["US", 5],
        ["DE", 2],
        ["GB", 1],
    ],
    "starter_sql": None,
    "hints": [
        "Join `orders` to `customers` on `customer_id`.",
        "Group by `country` and use `COUNT(*)`.",
    ],
    "editorial": "Join the fact table to the dimension, then group and count.",
}
```

---

## 4. Grading rules (read this before computing `expected_rows`)

Grading lives in [app/api/routers/submissions.py](app/api/routers/submissions.py).

1. **Read‑only / single statement.** The SQL must start with `SELECT` or `WITH`
   and contain no `insert/update/delete/drop/alter/truncate/create/grant/…` and
   no second statement (`;`). Otherwise the submission is an **error**.
2. **Columns** are compared **case‑insensitively** and **by position**; the
   count and order must match `expected_columns`.
3. **Rows** are compared **in order** — `expected_rows` must be in the exact
   order the prompt specifies. Always pin ordering with `ORDER BY` in the
   canonical solution and describe it in the prompt.
4. **Value normalization** (so DB types match JSON literals):
   - `NUMERIC`/`Decimal` → integer when whole (`660`), else float (`660.5`).
     Write whole money/counts as ints in `expected_rows`.
   - `DATE` → `"YYYY-MM-DD"` (e.g. `"2025-11-12"`).
   - `TIMESTAMP` / `TIME` → ISO‑8601 with a **`T` separator**
     (e.g. `"2025-11-12T10:00:00"`). **Not** a space.
   - `NULL` → JSON `null` (Python `None`).
   - Everything else → its string form.

### Timestamp gotcha

`orders.created_at` is a **TIMESTAMP**. So:

- To group/compare by day, cast: `created_at::date`.
- For month/year, use `EXTRACT(MONTH FROM created_at)` /
  `EXTRACT(YEAR FROM created_at)`.
- For an index‑friendly range over a single day, use a half‑open range:
  `created_at >= '2025-11-12' AND created_at < '2025-11-13'`.
- If your output **includes** `created_at`, the value must be ISO with `T`
  (e.g. `"2025-11-01T09:00:00"`).

---

## 5. Recipe: add a new challenge

1. **Pick tables.** Use only the §2 tables. If you genuinely need a new
   table/column, add it to `SHARED_TABLES` as a superset (keep existing
   challenges valid) and rebuild the sandbox.
2. **Write the prompt** with explicit output columns + ordering.
3. **Write the canonical solution SQL** (a single `SELECT`/`WITH`).
4. **Compute `expected_rows` for real** — never guess. Run the canonical SQL
   against the live sandbox and capture the normalized output, e.g.:

   ```powershell
   . .\venv\Scripts\Activate.ps1
   python -c "from app.db.db import SessionLocal; from sqlalchemy import text; db=SessionLocal(); db.execute(text('SET LOCAL search_path TO \"sandbox\"')); print([list(r) for r in db.execute(text('''<YOUR SQL>''')).fetchall()]); db.rollback()"
   ```

   Then format the values per §4 (Decimals→int, timestamps→`T`‑ISO).

5. **Append the dict** to `CHALLENGES` in [app/db/seed.py](app/db/seed.py)
   with a unique `id`/`slug`.
6. **Reseed and verify.** Note `seed_all` is idempotent and skips when
   challenges already exist, so do a full reset:

   ```powershell
   python -m app.db.init_db --drop
   ```

7. **Smoke‑test** by running your canonical solution through the real grader:

   ```python
   from app.db.db import SessionLocal
   from app import schemas
   from app.api.routers.submissions import _evaluate

   sql = """<YOUR CANONICAL SQL>"""
   with SessionLocal() as db:
       result, _ = _evaluate(
           schemas.SubmissionCreate(challenge_id="ch-your-id", sql=sql), db
       )
       print(result.status, result.message)   # expect: pass
   ```

---

## 6. Checklist

- [ ] Uses only the shared `sandbox` tables (or extends `SHARED_TABLES` as a superset).
- [ ] `id` and `slug` are unique; `schema_tables` built via `_tables(...)`.
- [ ] Prompt states exact output columns **and** ordering.
- [ ] `expected_columns` order matches the canonical solution.
- [ ] `expected_rows` computed from a real run and normalized (Decimals→int, timestamps→`T`‑ISO, dates→`YYYY-MM-DD`, NULL→`null`).
- [ ] Canonical solution is a single read‑only `SELECT`/`WITH`.
- [ ] `python -m app.db.init_db --drop` succeeds; grader returns `pass`.
