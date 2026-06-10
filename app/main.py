from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import (
    challenge_router,
    track_router,
    submissions_router,
    user_router,
    interview_sessions_router,
)

app = FastAPI(title="SQLdle API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Error envelope: { "error": { "code": str, "message": str } } ----------

_STATUS_TO_CODE = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    409: "conflict",
    422: "validation_error",
    429: "rate_limited",
    500: "internal_error",
}


@app.exception_handler(HTTPException)
async def _http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
    code = _STATUS_TO_CODE.get(exc.status_code, "error")
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": code, "message": str(exc.detail)}},
    )


@app.exception_handler(RequestValidationError)
async def _validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"error": {"code": "validation_error", "message": str(exc.errors())}},
    )


# --- Routers ---------------------------------------------------------------

app.include_router(challenge_router, prefix="/api/challenges", tags=["challenges"])
app.include_router(track_router, prefix="/api/tracks", tags=["tracks"])
app.include_router(submissions_router, prefix="/api/submissions", tags=["submissions"])
app.include_router(user_router, prefix="/api/user", tags=["user"])
app.include_router(
    interview_sessions_router,
    prefix="/api/interview-sessions",
    tags=["interview-sessions"],
)


@app.get("/")
def root():
    return {"message": "SQLdle API is running!"}
