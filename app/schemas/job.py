from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class JobCreate(BaseModel):
    task: str
    agent_id: str
    project_id: Optional[str] = None
    job_type: str = "IMMEDIATE" # IMMEDIATE, SCHEDULED
    priority: int = 0
    max_attempts: int = 3
    delay_seconds: int = 0
    override_config: Optional[Dict[str, Any]] = None

class JobAttemptResponse(BaseModel):
    id: str
    job_id: str
    attempt_number: int
    status: str
    error_message: Optional[str] = None
    execution_latency_ms: float
    started_at: datetime
    completed_at: datetime

    model_config = ConfigDict(from_attributes=True)

class JobResponse(BaseModel):
    id: str
    queue_message_id: Optional[str] = None
    execution_id: Optional[str] = None
    job_type: str
    status: str
    priority: int
    scheduled_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    attempts: int
    max_attempts: int
    error: Optional[str] = None
    metadata_info: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    attempts_history: Optional[List[JobAttemptResponse]] = None

    model_config = ConfigDict(from_attributes=True)
