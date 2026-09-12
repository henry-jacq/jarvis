from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.models.executions import Execution, ExecutionEvent, ExecutionApprovalRequest
from app.runtime.executor import SimpleAgentExecutor
from app.runtime.workflow_executor import StaticWorkflowExecutor
from app.services.workflow_service import WorkflowService
from app.schemas.execution import (
    ExecutionRequest,
    ExecutionResponse,
    ExecutionEventResponse,
    ApprovalRequestResponse,
    ApprovalDecisionRequest
)

router = APIRouter(prefix="/executions", tags=["Executions"])

@router.get("/approvals/pending", response_model=List[ApprovalRequestResponse])
def list_pending_approvals(db: Session = Depends(get_db)):
    wf_svc = WorkflowService(db)
    return wf_svc.list_pending_approvals()

@router.post("/{execution_id}/approvals/{approval_id}/decision", response_model=ExecutionResponse)
def submit_approval_decision(
    execution_id: str,
    approval_id: str,
    payload: ApprovalDecisionRequest,
    db: Session = Depends(get_db)
):
    wf_executor = StaticWorkflowExecutor(db)
    try:
        execution = wf_executor.resume_execution(
            execution_id=execution_id,
            approval_id=approval_id,
            decision=payload.decision,
            feedback=payload.feedback
        )
        return execution
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit decision: {str(e)}")

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

