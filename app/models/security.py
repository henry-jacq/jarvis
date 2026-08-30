import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, JSON, ForeignKey
from app.core.db import Base

def generate_uuid():
    return str(uuid.uuid4())

def utc_now():
    return datetime.now(timezone.utc)

class PermissionPolicy(Base):
    __tablename__ = "permission_policies"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    allowed_tools = Column(JSON, nullable=False, default=list) # e.g. ["read_project_file", "git_diff"]
    denied_tools = Column(JSON, nullable=False, default=list)  # e.g. ["delete_file", "production_deploy"]
    requires_approval = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), default=utc_now)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    actor = Column(String(255), nullable=False, default="system")
    action = Column(String(255), nullable=False) # e.g. agent_version_published, tool_executed, tool_denied
    agent_id = Column(String(36), nullable=True)
    project_id = Column(String(36), nullable=True)
    execution_id = Column(String(36), nullable=True)
    tool_name = Column(String(255), nullable=True)
    decision = Column(String(50), nullable=False, default="ALLOW") # ALLOW, DENY, REVIEW
    details = Column(JSON, nullable=True, default=dict)
    timestamp = Column(DateTime(timezone=True), default=utc_now)
