import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, JSON, ForeignKey, Integer
from app.core.db import Base

def generate_uuid():
    return str(uuid.uuid4())

def utc_now():
    return datetime.now(timezone.utc)

class Prompt(Base):
    __tablename__ = "prompts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class PromptVersion(Base):
    __tablename__ = "prompt_versions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    prompt_id = Column(String(36), ForeignKey("prompts.id"), nullable=False)
    version = Column(Integer, nullable=False)
    template = Column(Text, nullable=False)
    variables = Column(JSON, nullable=True, default=list)
    created_at = Column(DateTime(timezone=True), default=utc_now)
