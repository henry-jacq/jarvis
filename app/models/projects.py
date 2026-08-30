import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, JSON, ForeignKey
from app.core.db import Base

def generate_uuid():
    return str(uuid.uuid4())

def utc_now():
    return datetime.now(timezone.utc)

class Project(Base):
    __tablename__ = "projects"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    application_id = Column(String(36), ForeignKey("applications.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default="active")
    repository = Column(String(512), nullable=True)
    config = Column(JSON, nullable=True, default=dict)
    # Structured project context (e.g. database schema, primary language, architecture decisions, etc.)
    structured_context = Column(JSON, nullable=True, default=dict)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
