from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class ToolBase(BaseModel):
    name: str
    description: str
    input_schema: Dict[str, Any]
    output_schema: Optional[Dict[str, Any]] = None
    runtime: str = "builtin"
    risk_level: str = "LOW"
    status: str = "active"

class ToolCreate(ToolBase):
    pass

class ToolResponse(ToolBase):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
