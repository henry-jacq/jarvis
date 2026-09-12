from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.services.workflow_service import WorkflowService
from app.runtime.workflow_executor import StaticWorkflowExecutor
from app.schemas.workflow import (
    WorkflowCreate,
    WorkflowResponse,
    WorkflowVersionCreate,
    WorkflowVersionResponse,
    WorkflowExecutionRequest,
    ExecutionCheckpointResponse
)
from app.schemas.execution import ExecutionResponse

router = APIRouter(prefix="/workflows", tags=["Workflows"])

@router.post("", response_model=WorkflowResponse)
def create_workflow(payload: WorkflowCreate, db: Session = Depends(get_db)):
    service = WorkflowService(db)
    return service.create_workflow(payload)

@router.get("", response_model=List[WorkflowResponse])
def list_workflows(db: Session = Depends(get_db)):
    service = WorkflowService(db)
    return service.list_workflows()

@router.get("/{workflow_id}", response_model=WorkflowResponse)
def get_workflow(workflow_id: str, db: Session = Depends(get_db)):
    service = WorkflowService(db)
    wf = service.get_workflow(workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found.")
    return wf

@router.post("/{workflow_id}/versions", response_model=WorkflowVersionResponse)
def publish_workflow_version(workflow_id: str, payload: WorkflowVersionCreate, db: Session = Depends(get_db)):
    service = WorkflowService(db)
    wf = service.get_workflow(workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found.")
    return service.publish_version(workflow_id, payload)

@router.post("/submit", response_model=ExecutionResponse)
def submit_workflow_execution(payload: WorkflowExecutionRequest, db: Session = Depends(get_db)):
    executor = StaticWorkflowExecutor(db)
    try:
        return executor.execute(
            workflow_id=payload.workflow_id,
            task=payload.task,
            project_id=payload.project_id,
            override_config=payload.override_config
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Workflow execution error: {str(e)}")

@router.get("/executions/{execution_id}/checkpoints", response_model=List[ExecutionCheckpointResponse])
def get_execution_checkpoints(execution_id: str, db: Session = Depends(get_db)):
    service = WorkflowService(db)
    return service.get_execution_checkpoints(execution_id)
