# SQLdle frontend ↔ Python API contract

The frontend talks to a single API facade in `src/api/client.ts`. Today it points to a `mockClient`. To plug in your Python server, implement these endpoints (FastAPI is recommended) and add an `httpClient` that conforms to the same `ApiClient` interface.

All responses are JSON. Errors return HTTP 4xx/5xx with `{ "error": { "code": string, "message": string } }`.

## Auth (future)

For MVP the frontend assumes a single signed-in user. Add JWT bearer auth when ready:

- `POST /api/auth/register` → `{ token }`
- `POST /api/auth/login` → `{ token }`
- `POST /api/auth/refresh` → `{ token }`

## Challenges

- `GET /api/challenges` → `Challenge[]`
- `GET /api/challenges/{id_or_slug}` → `Challenge`
- `GET /api/challenges/daily` → `{ date: "YYYY-MM-DD", challenge: Challenge }`

`Challenge` shape (mirrors `src/types/domain.ts`):

```jsonc
{
  "id": "ch-top-customers",
  "slug": "top-customers-by-revenue",
  "title": "Top customers by revenue",
  "difficulty": "easy | medium | hard | expert",
  "topics": ["aggregation", "joins"],
  "estimatedMinutes": 8,
  "prompt": "markdown-friendly text",
  "schema": [
    {
      "name": "customers",
      "columns": [{ "name": "id", "type": "INT", "note": "PK" }],
      "sampleRows": [{ "id": 1, "name": "Acme" }],
    },
  ],
  "expectedColumns": ["customer_name", "total_revenue"],
  "expectedRows": [["Acme Corp", 660]],
  "starterSql": "SELECT ...",
  "hints": [{ "id": "h1", "text": "..." }],
  "editorial": "explanation shown after solving",
}
```

## Tracks

- `GET /api/tracks` → `Track[]`
- `GET /api/tracks/{id_or_slug}` → `Track`

A `Track` contains `lessons[]`, each lesson has an ordered `challengeIds[]`.

## Submissions

- `POST /api/submissions`
  - Request: `{ "challengeId": string, "sql": string }`
  - Response: `SubmissionResult`

```jsonc
{
  "id": "sub-...",
  "challengeId": "ch-...",
  "status": "pass | fail | error",
  "message": "string for the user",
  "columns": ["..."],
  "rowsReturned": [["..."]],
  "durationMs": 124,
  "createdAt": "ISO-8601",
}
```

### Server-side execution notes (non-binding suggestions)

- Run user SQL in an isolated, read-only sandbox (separate Postgres/SQLite per challenge or a fresh schema per submission).
- Hard-cap query time (e.g. 5s) and memory.
- Reject statements that are not `SELECT` or `WITH ... SELECT` for safety.
- Compare results semantically: same columns (case-insensitive), same row set (with order if the prompt specifies ORDER BY).

## User progress

- `GET /api/user/progress` → `UserProgress`

Includes totals, streak, xp, level, topic mastery (0..1), recent submissions, achievements, and per-track lesson counts.

## Interview sessions

- `POST /api/interview-sessions`
  - Request: `{ "difficulty": Difficulty, "questionCount": number }`
  - Response: `InterviewSession` with `challengeIds[]`, `timeLimitSec`, `createdAt`.
- `GET /api/interview-sessions/{id}` → `InterviewSession`
- `POST /api/interview-sessions/{id}/finish` → summary (future)

## Pagination

For list endpoints, support `?limit=` and `?cursor=` query params. The frontend currently fetches small lists, so simple arrays are fine for MVP.

## CORS

Allow the frontend dev origin (`http://localhost:5173`) and your production origin.

## Wiring the real client

When ready, add `src/api/httpClient.ts` exporting an `ApiClient`-shaped object that calls `fetch` against your server, then in `src/api/client.ts` swap:

```ts
export const api: ApiClient = httpClient; // instead of mockClient
```

No UI code needs to change.
