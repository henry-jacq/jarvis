from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from app.models.projects import Project
from app.models.conversations import Conversation
from app.schemas.project import ProjectCreate

class ProjectService:
    def __init__(self, db: Session):
        self.db = db

    def create_project(self, payload: ProjectCreate) -> Project:
        project = Project(
            name=payload.name,
            objective=payload.objective,
            description=payload.description,
            status=payload.status,
            repository=payload.repository,
            project_settings=payload.project_settings or {},
            structured_context=payload.structured_context or {},
            project_tasks=payload.project_tasks or [],
            project_documents=payload.project_documents or []
        )
        self.db.add(project)
        self.db.commit()
        self.db.refresh(project)
        return project

    def get_project(self, project_id: str) -> Optional[Project]:
        return self.db.query(Project).filter(Project.id == project_id).first()

    def list_projects(self) -> List[Project]:
        return self.db.query(Project).all()

    def add_project_task(self, project_id: str, task: Dict[str, Any]) -> Project:
        project = self.get_project(project_id)
        if not project:
            raise ValueError(f"Project '{project_id}' not found.")
        tasks = list(project.project_tasks or [])
        tasks.append(task)
        project.project_tasks = tasks
        self.db.commit()
        self.db.refresh(project)
        return project

    def add_project_document(self, project_id: str, document: Dict[str, Any]) -> Project:
        project = self.get_project(project_id)
        if not project:
            raise ValueError(f"Project '{project_id}' not found.")
        docs = list(project.project_documents or [])
        docs.append(document)
        project.project_documents = docs
        self.db.commit()
        self.db.refresh(project)
        return project

    def list_attached_conversations(self, project_id: str) -> List[Conversation]:
        return self.db.query(Conversation).filter(Conversation.project_id == project_id).all()
