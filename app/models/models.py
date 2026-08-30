import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, JSON, Boolean, Integer, ForeignKey
from app.core.db import Base

def generate_uuid():
    return str(uuid.uuid4())

def utc_now():
    return datetime.now(timezone.utc)

class ModelProvider(Base):
    __tablename__ = "model_providers"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(100), nullable=False, unique=True) # e.g. ollama, openai, anthropic
    base_url = Column(String(512), nullable=True)
    status = Column(String(50), nullable=False, default="active")
    created_at = Column(DateTime(timezone=True), default=utc_now)


class ModelConfig(Base):
    __tablename__ = "models"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    provider_id = Column(String(36), ForeignKey("model_providers.id"), nullable=True)
    provider_name = Column(String(100), nullable=False) # e.g. ollama
    model_name = Column(String(100), nullable=False) # e.g. llama3.2, gpt-4o
    context_limit = Column(Integer, nullable=False, default=4096)
    supports_tools = Column(Boolean, nullable=False, default=True)
    supports_structured_output = Column(Boolean, nullable=False, default=True)
    supports_vision = Column(Boolean, nullable=False, default=False)
    status = Column(String(50), nullable=False, default="active")
    created_at = Column(DateTime(timezone=True), default=utc_now)
