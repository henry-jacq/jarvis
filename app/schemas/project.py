from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class ProjectBase(BaseModel):
    name: str
    objective: Optional[str] = None
    description: Optional[str] = None
    status: str = "active"
    repository: Optional[str] = None
    project_settings: Optional[Dict[str, Any]] = None
    structured_context: Optional[Dict[str, Any]] = None
    project_tasks: Optional[List[Dict[str, Any]]] = None
    project_documents: Optional[List[Dict[str, Any]]] = None

class ProjectCreate(ProjectBase):
    pass

class ProjectResponse(ProjectBase):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
