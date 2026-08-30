from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class ApplicationBase(BaseModel):
    name: str
    description: Optional[str] = None
    status: str = "active"
    config: Optional[Dict[str, Any]] = None

class ApplicationCreate(ApplicationBase):
    pass

class ApplicationResponse(ApplicationBase):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
