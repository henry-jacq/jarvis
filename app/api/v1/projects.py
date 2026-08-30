from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.services.project_service import ProjectService
from app.schemas.project import ProjectCreate, ProjectResponse

router = APIRouter(prefix="/projects", tags=["Projects"])

@router.post("", response_model=ProjectResponse)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    service = ProjectService(db)
    return service.create_project(payload)

@router.get("", response_model=List[ProjectResponse])
def list_projects(application_id: Optional[str] = None, db: Session = Depends(get_db)):
    service = ProjectService(db)
    return service.list_projects(application_id=application_id)

@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project_id: str, db: Session = Depends(get_db)):
    service = ProjectService(db)
    project = service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    return project
