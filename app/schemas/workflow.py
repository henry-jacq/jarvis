from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class WorkflowNodeCreate(BaseModel):
    node_key: str
    node_type: str = "agent" # agent, tool, condition, human_approval
    agent_id: Optional[str] = None
    prompt_overlay: Optional[str] = None
    config_override: Optional[Dict[str, Any]] = None
    input_mapping: Optional[Dict[str, Any]] = None
    output_mapping: Optional[Dict[str, Any]] = None

class WorkflowNodeResponse(WorkflowNodeCreate):
    id: str
    workflow_version_id: str

    model_config = ConfigDict(from_attributes=True)

class WorkflowEdgeCreate(BaseModel):
    source_node_key: str
    target_node_key: str
    condition_expression: Optional[str] = None

class WorkflowEdgeResponse(WorkflowEdgeCreate):
    id: str
    workflow_version_id: str

    model_config = ConfigDict(from_attributes=True)

class WorkflowAgentBindingCreate(BaseModel):
    agent_id: str
    role: str
    prompt_overlay: Optional[str] = None
    context_policy: Optional[Dict[str, Any]] = None
    tool_policy: Optional[Dict[str, Any]] = None
    config_override: Optional[Dict[str, Any]] = None

class WorkflowAgentBindingResponse(WorkflowAgentBindingCreate):
    id: str
    workflow_id: str
    workflow_version_id: str

    model_config = ConfigDict(from_attributes=True)

class WorkflowVersionCreate(BaseModel):
    input_schema: Dict[str, Any] = {"type": "object"}
    output_schema: Dict[str, Any] = {"type": "object"}
    state_schema: Dict[str, Any] = {"type": "object"}
    nodes: List[WorkflowNodeCreate]
    edges: List[WorkflowEdgeCreate]
    agent_bindings: List[WorkflowAgentBindingCreate]
    config: Optional[Dict[str, Any]] = None

class WorkflowVersionResponse(BaseModel):
    id: str
    workflow_id: str
    version: int
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    state_schema: Dict[str, Any]
    config: Optional[Dict[str, Any]]
    published_at: datetime
    nodes: Optional[List[WorkflowNodeResponse]] = None
    edges: Optional[List[WorkflowEdgeResponse]] = None
    agent_bindings: Optional[List[WorkflowAgentBindingResponse]] = None

    model_config = ConfigDict(from_attributes=True)

class WorkflowCreate(BaseModel):
    name: str
    description: Optional[str] = None
    initial_version: WorkflowVersionCreate

class WorkflowResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    status: str
    active_version_id: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class WorkflowExecutionRequest(BaseModel):
    workflow_id: str
    task: str
    project_id: Optional[str] = None
    input_params: Optional[Dict[str, Any]] = None
    override_config: Optional[Dict[str, Any]] = None

class ExecutionCheckpointResponse(BaseModel):
    id: str
    execution_id: str
    checkpoint_key: str
    node_key: str
    state_snapshot: Dict[str, Any]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
