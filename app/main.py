from fastapi import FastAPI
from app.api import challenge_router, track_router, submissions_router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Allow all origins (for testing purposes)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(challenge_router, prefix="/challenges", tags=["challenges"])
app.include_router(track_router, prefix="/tracks", tags=["tracks"])
app.include_router(submissions_router, prefix="/submissions", tags=["submissions"])


@app.get("/")
def root():
    return {"message": "SQLdle API is running!"}
