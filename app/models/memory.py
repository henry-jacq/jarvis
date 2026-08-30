import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, JSON, ForeignKey, Float
from app.core.db import Base

def generate_uuid():
    return str(uuid.uuid4())

def utc_now():
    return datetime.now(timezone.utc)

class GlobalMemory(Base):
    __tablename__ = "global_memory"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    application_id = Column(String(36), ForeignKey("applications.id"), nullable=True)
    category = Column(String(100), nullable=False, default="general") # preferences, conventions, terminology
    key = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    importance = Column(Float, nullable=False, default=1.0)
    provenance = Column(JSON, nullable=True, default=dict)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class AgentMemory(Base):
    __tablename__ = "agent_memory"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    agent_id = Column(String(36), ForeignKey("agents.id"), nullable=False)
    category = Column(String(100), nullable=False, default="learned_insight")
    key = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    importance = Column(Float, nullable=False, default=1.0)
    provenance = Column(JSON, nullable=True, default=dict)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class ProjectMemory(Base):
    __tablename__ = "project_memory"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    category = Column(String(100), nullable=False, default="architecture") # architecture, decision, convention, requirement
    key = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    importance = Column(Float, nullable=False, default=1.0)
    provenance = Column(JSON, nullable=True, default=dict)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
