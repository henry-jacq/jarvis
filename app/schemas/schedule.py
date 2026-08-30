from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class ScheduleCreate(BaseModel):
    name: str
    agent_id: str
    project_id: Optional[str] = None
    schedule_expression: str # e.g. "cron:0 9 * * *" or "interval:3600"
    timezone: str = "UTC"
    enabled: bool = True
    task_input: Dict[str, Any]

class ScheduleResponse(BaseModel):
    id: str
    name: str
    agent_id: str
    project_id: Optional[str] = None
    schedule_expression: str
    timezone: str
    enabled: bool
    next_run_at: Optional[datetime] = None
    last_run_at: Optional[datetime] = None
    task_input: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
