from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class QueueMessageCreate(BaseModel):
    topic: str = "default"
    payload_type: str
    payload: Dict[str, Any]
    priority: int = 0
    max_attempts: int = 3
    delay_seconds: int = 0

class QueueMessageResponse(BaseModel):
    id: str
    topic: str
    payload_type: str
    payload: Dict[str, Any]
    status: str
    priority: int
    attempts: int
    max_attempts: int
    available_at: datetime
    locked_at: Optional[datetime] = None
    locked_by: Optional[str] = None
    last_error: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
