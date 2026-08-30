from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class ProjectBase(BaseModel):
    name: str
    application_id: str
    description: Optional[str] = None
    status: str = "active"
    repository: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    structured_context: Optional[Dict[str, Any]] = None

class ProjectCreate(ProjectBase):
    pass

class ProjectResponse(ProjectBase):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
