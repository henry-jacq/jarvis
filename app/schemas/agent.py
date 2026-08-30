from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class AgentVersionBase(BaseModel):
    system_prompt: str
    model_provider: str = "ollama"
    model_name: str = "llama3.2"
    temperature: float = 0.7
    tool_policy: Dict[str, Any] = {"allowed": [], "denied": []}
    memory_policy: Dict[str, Any] = {"read_scopes": ["global", "agent", "project"], "write": True}
    context_policy: Dict[str, Any] = {"max_tokens": 4096}
    config: Optional[Dict[str, Any]] = None

class AgentVersionCreate(AgentVersionBase):
    pass

class AgentVersionResponse(AgentVersionBase):
    id: str
    agent_id: str
    version: int
    published_at: datetime

    model_config = ConfigDict(from_attributes=True)

class AgentBase(BaseModel):
    name: str
    role: str
    purpose: Optional[str] = None
    application_id: Optional[str] = None
    status: str = "active"

class AgentCreate(AgentBase):
    initial_version: AgentVersionCreate

class AgentResponse(AgentBase):
    id: str
    active_version_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
