import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, JSON, ForeignKey, Integer, Float
from app.core.db import Base

def generate_uuid():
    return str(uuid.uuid4())

def utc_now():
    return datetime.now(timezone.utc)

class Agent(Base):
    __tablename__ = "agents"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    application_id = Column(String(36), ForeignKey("applications.id"), nullable=True)
    name = Column(String(255), nullable=False, unique=True)
    role = Column(String(255), nullable=False)
    purpose = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default="active")
    active_version_id = Column(String(36), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class AgentVersion(Base):
    __tablename__ = "agent_versions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    agent_id = Column(String(36), ForeignKey("agents.id"), nullable=False)
    version = Column(Integer, nullable=False)
    system_prompt = Column(Text, nullable=False)
    model_provider = Column(String(100), nullable=False, default="ollama")
    model_name = Column(String(100), nullable=False, default="llama3.2")
    temperature = Column(Float, nullable=False, default=0.7)
    
    # Policies stored as JSON configurations
    tool_policy = Column(JSON, nullable=False, default=dict) # e.g. {"allowed": ["read_file"], "denied": ["delete_file"]}
    memory_policy = Column(JSON, nullable=False, default=dict) # e.g. {"read_scopes": ["global", "agent", "project"], "write": true}
    context_policy = Column(JSON, nullable=False, default=dict) # e.g. {"max_tokens": 4096}
    
    config = Column(JSON, nullable=True, default=dict)
    published_at = Column(DateTime(timezone=True), default=utc_now)
