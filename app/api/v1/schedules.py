from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.services.scheduler_service import SchedulerService
from app.schemas.schedule import ScheduleCreate, ScheduleResponse

router = APIRouter(prefix="/schedules", tags=["Schedules"])

@router.post("", response_model=ScheduleResponse)
def create_schedule(payload: ScheduleCreate, db: Session = Depends(get_db)):
    service = SchedulerService(db)
    return service.create_schedule(payload)

@router.get("", response_model=List[ScheduleResponse])
def list_schedules(db: Session = Depends(get_db)):
    service = SchedulerService(db)
    return service.list_schedules()

@router.get("/{schedule_id}", response_model=ScheduleResponse)
def get_schedule(schedule_id: str, db: Session = Depends(get_db)):
    service = SchedulerService(db)
    sched = service.get_schedule(schedule_id)
    if not sched:
        raise HTTPException(status_code=404, detail="Schedule not found.")
    return sched

@router.post("/evaluate")
def evaluate_schedules(db: Session = Depends(get_db)):
    service = SchedulerService(db)
    triggered = service.evaluate_schedules()
    return {"status": "success", "triggered_jobs": triggered}
