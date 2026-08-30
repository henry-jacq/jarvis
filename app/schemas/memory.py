from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class MemoryCandidateCreate(BaseModel):
    scope: str # "global", "agent", or "project"
    target_id: Optional[str] = None # agent_id or project_id if scope is agent/project
    category: str = "general"
    key: str
    content: str
    importance: float = 1.0
    provenance: Optional[Dict[str, Any]] = None

class MemoryItemResponse(BaseModel):
    id: str
    scope: str
    target_id: Optional[str] = None
    category: str
    key: str
    content: str
    importance: float
    provenance: Optional[Dict[str, Any]] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
