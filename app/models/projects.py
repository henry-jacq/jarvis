import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, JSON
from app.core.db import Base

def generate_uuid():
    return str(uuid.uuid4())

def utc_now():
    return datetime.now(timezone.utc)

class Project(Base):
    __tablename__ = "projects"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    objective = Column(Text, nullable=True) # High-level project objective
    description = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default="active")
    repository = Column(String(512), nullable=True)
    
    # Project Configuration & Knowledge Collections
    project_settings = Column(JSON, nullable=True, default=dict)
    structured_context = Column(JSON, nullable=True, default=dict)
    project_tasks = Column(JSON, nullable=True, default=list) # [{id, title, status, priority}]
    project_documents = Column(JSON, nullable=True, default=list) # [{id, title, content, type}]
    
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
