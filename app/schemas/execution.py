from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class ExecutionRequest(BaseModel):
    task: str
    agent_id: str
    project_id: Optional[str] = None
    input_params: Optional[Dict[str, Any]] = None
    override_config: Optional[Dict[str, Any]] = None

class ExecutionEventResponse(BaseModel):
    id: str
    event_type: str
    payload: Dict[str, Any]
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)

class ExecutionResponse(BaseModel):
    id: str
    type: str
    agent_id: Optional[str]
    agent_version_id: Optional[str]
    project_id: Optional[str]
    status: str
    input_data: Dict[str, Any]
    output_data: Optional[Dict[str, Any]]
    error_message: Optional[str]
    input_tokens: int
    output_tokens: int
    total_tokens: int
    execution_time_ms: float
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    events: Optional[List[ExecutionEventResponse]] = None

    model_config = ConfigDict(from_attributes=True)

class ApprovalDecisionRequest(BaseModel):
    decision: str # APPROVED, REJECTED
    feedback: Optional[str] = None

class ApprovalRequestResponse(BaseModel):
    id: str
    execution_id: str
    node_key: Optional[str]
    request_type: str
    tool_name: Optional[str]
    tool_args: Optional[Dict[str, Any]]
    status: str
    reviewer_feedback: Optional[str]
    created_at: datetime
    resolved_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)

