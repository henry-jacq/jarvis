from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.models.executions import Execution, ExecutionEvent
from app.runtime.executor import SimpleAgentExecutor
from app.schemas.execution import ExecutionRequest, ExecutionResponse, ExecutionEventResponse

router = APIRouter(prefix="/executions", tags=["Executions"])

@router.post("/submit", response_model=ExecutionResponse)
def submit_execution(payload: ExecutionRequest, db: Session = Depends(get_db)):
    executor = SimpleAgentExecutor(db)
    try:
        execution = executor.execute(
            task=payload.task,
            agent_id=payload.agent_id,
            project_id=payload.project_id,
            override_config=payload.override_config
        )
        return execution
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Execution error: {str(e)}")

@router.get("", response_model=List[ExecutionResponse])
def list_executions(db: Session = Depends(get_db)):
    return db.query(Execution).order_by(Execution.created_at.desc()).all()

@router.get("/{execution_id}", response_model=ExecutionResponse)
def get_execution(execution_id: str, db: Session = Depends(get_db)):
    execution = db.query(Execution).filter(Execution.id == execution_id).first()
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found.")
    return execution

@router.get("/{execution_id}/events", response_model=List[ExecutionEventResponse])
def get_execution_events(execution_id: str, db: Session = Depends(get_db)):
    events = db.query(ExecutionEvent).filter(
        ExecutionEvent.execution_id == execution_id
    ).order_by(ExecutionEvent.timestamp.asc()).all()
    return events
