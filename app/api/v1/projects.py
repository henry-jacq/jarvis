from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.services.project_service import ProjectService
from app.schemas.project import ProjectCreate, ProjectResponse
from app.schemas.conversation import ConversationResponse

router = APIRouter(prefix="/projects", tags=["Projects"])

@router.post("", response_model=ProjectResponse)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    service = ProjectService(db)
    return service.create_project(payload)

@router.get("", response_model=List[ProjectResponse])
def list_projects(db: Session = Depends(get_db)):
    service = ProjectService(db)
    return service.list_projects()

@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project_id: str, db: Session = Depends(get_db)):
    service = ProjectService(db)
    project = service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    return project

@router.post("/{project_id}/tasks", response_model=ProjectResponse)
def add_project_task(project_id: str, task: Dict[str, Any], db: Session = Depends(get_db)):
    service = ProjectService(db)
    try:
        return service.add_project_task(project_id, task)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/{project_id}/documents", response_model=ProjectResponse)
def add_project_document(project_id: str, document: Dict[str, Any], db: Session = Depends(get_db)):
    service = ProjectService(db)
    try:
        return service.add_project_document(project_id, document)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/{project_id}/conversations", response_model=List[ConversationResponse])
def list_attached_conversations(project_id: str, db: Session = Depends(get_db)):
    service = ProjectService(db)
    return service.list_attached_conversations(project_id)
