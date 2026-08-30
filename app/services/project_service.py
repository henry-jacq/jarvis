from typing import Optional, List
from sqlalchemy.orm import Session
from app.models.projects import Project
from app.schemas.project import ProjectCreate

class ProjectService:
    def __init__(self, db: Session):
        self.db = db

    def create_project(self, payload: ProjectCreate) -> Project:
        project = Project(
            application_id=payload.application_id,
            name=payload.name,
            description=payload.description,
            status=payload.status,
            repository=payload.repository,
            config=payload.config or {},
            structured_context=payload.structured_context or {}
        )
        self.db.add(project)
        self.db.commit()
        self.db.refresh(project)
        return project

    def get_project(self, project_id: str) -> Optional[Project]:
        return self.db.query(Project).filter(Project.id == project_id).first()

    def list_projects(self, application_id: Optional[str] = None) -> List[Project]:
        query = self.db.query(Project)
        if application_id:
            query = query.filter(Project.application_id == application_id)
        return query.all()
