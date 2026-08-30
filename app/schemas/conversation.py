from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class MessageCreate(BaseModel):
    role: str # user, assistant, system, tool
    content: str
    metadata_info: Optional[Dict[str, Any]] = None

class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    metadata_info: Optional[Dict[str, Any]]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ConversationCreate(BaseModel):
    title: Optional[str] = "New Conversation"
    project_id: Optional[str] = None
    initial_message: Optional[MessageCreate] = None
    metadata_info: Optional[Dict[str, Any]] = None

class ConversationResponse(BaseModel):
    id: str
    title: str
    status: str
    project_id: Optional[str]
    metadata_info: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime
    messages: Optional[List[MessageResponse]] = None

    model_config = ConfigDict(from_attributes=True)

class ProjectSuggestionResponse(BaseModel):
    conversation_id: str
    suggest_project: bool
    reason: str
    suggested_title: str
    suggested_objective: str
