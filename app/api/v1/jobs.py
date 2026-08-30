from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.services.job_manager import JobManager
from app.schemas.job import JobCreate, JobResponse, JobAttemptResponse

router = APIRouter(prefix="/jobs", tags=["Jobs"])

@router.post("/submit", response_model=JobResponse)
def submit_job(payload: JobCreate, db: Session = Depends(get_db)):
    manager = JobManager(db)
    return manager.submit_job(payload)

@router.get("", response_model=List[JobResponse])
def list_jobs(db: Session = Depends(get_db)):
    manager = JobManager(db)
    return manager.list_jobs()

@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: str, db: Session = Depends(get_db)):
    manager = JobManager(db)
    job = manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    job_dict = JobResponse.model_validate(job)
    job_dict.attempts_history = [JobAttemptResponse.model_validate(a) for a in manager.get_job_attempts(job_id)]
    return job_dict

@router.post("/{job_id}/cancel", response_model=JobResponse)
def cancel_job(job_id: str, db: Session = Depends(get_db)):
    manager = JobManager(db)
    try:
        return manager.cancel_job(job_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/{job_id}/attempts", response_model=List[JobAttemptResponse])
def get_job_attempts(job_id: str, db: Session = Depends(get_db)):
    manager = JobManager(db)
    return manager.get_job_attempts(job_id)
