from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text

from app import schemas
from app.db import models
from app.db.db import get_db
from datetime import datetime

router = APIRouter()

def eval_submission(submission: schemas.SubmissionCreate, db: Session) -> schemas.SubmissionResultOut:
    # Fetch the challenge
    challenge = db.query(models.Challenge).filter(models.Challenge.id == submission.challenge_id).first()
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found")
    
    try:
        submission_results = db.execute(text(submission.sql)).fetchall()

    except Exception as e:
        status = "error"
        message = f"Error executing SQL: {str(e)}"
        return schemas.SubmissionResultOut(id = f"sub_{uuid4()}", challenge_id= submission.challenge_id, status=status, message=message, columns=[], rows_returned=[], duration_ms=0, created_at=datetime.now())
    
    ms_duration = submission_results._metadata._execution_time * 1000 # Convert 
    submission_columns = submission_results[0].keys() if submission_results else []
    submission_rows = [list(row) for row in submission_results]

    if submission_columns == challenge.expected_columns and submission_rows == challenge.expected_rows:
        status = "pass"
        message = "Correct solution!"
    elif submission_columns == challenge.expected_columns:
        status = "fail"
        message = "Partially correct - columns match but rows do not."
    else:
        status = "fail"
        message = "Incorrect solution - columns do not match."
    
    return schemas.SubmissionResultOut(id = f"sub_{uuid4()}", challenge_id= submission.challenge_id, status=status, message=message, columns=submission_columns, rows_returned=submission_rows, duration_ms=ms_duration, created_at=datetime.now())

@router.post("/", response_model = schemas.SubmissionResultOut)
def submit_solution(submission: schemas.SubmissionCreate, db: Session = Depends(get_db)) -> schemas.SubmissionResultOut:
    try:
        result = eval_submission(submission, db)
        return result

    except Exception as e:
        print("Error evaluating submission:", e)
        raise HTTPException(status_code=500, detail=str(e))
        