import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, JSON, ForeignKey, Integer, Float
from app.core.db import Base

def generate_uuid():
    return str(uuid.uuid4())

def utc_now():
    return datetime.now(timezone.utc)

class Execution(Base):
    __tablename__ = "executions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    parent_execution_id = Column(String(36), ForeignKey("executions.id"), nullable=True)
    type = Column(String(50), nullable=False, default="SIMPLE") # SIMPLE, STATIC_WORKFLOW, DYNAMIC_WORKFLOW
    agent_id = Column(String(36), ForeignKey("agents.id"), nullable=True)
    agent_version_id = Column(String(36), ForeignKey("agent_versions.id"), nullable=True)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=True)
    
    input_data = Column(JSON, nullable=False, default=dict)
    output_data = Column(JSON, nullable=True, default=dict)
    status = Column(String(50), nullable=False, default="PENDING") # PENDING, QUEUED, RUNNING, COMPLETED, FAILED, CANCELLED
    error_message = Column(Text, nullable=True)
    
    # Snapshot of configuration and context used
    configuration_snapshot = Column(JSON, nullable=True, default=dict)
    
    # Telemetry
    input_tokens = Column(Integer, nullable=False, default=0)
    output_tokens = Column(Integer, nullable=False, default=0)
    total_tokens = Column(Integer, nullable=False, default=0)
    execution_time_ms = Column(Float, nullable=False, default=0.0)
    
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)


class ExecutionEvent(Base):
    __tablename__ = "execution_events"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    execution_id = Column(String(36), ForeignKey("executions.id"), nullable=False)
    event_type = Column(String(100), nullable=False) # agent_start, tool_request, permission_evaluation, tool_response, agent_finish
    payload = Column(JSON, nullable=False, default=dict)
    timestamp = Column(DateTime(timezone=True), default=utc_now)


class Artifact(Base):
    __tablename__ = "artifacts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    execution_id = Column(String(36), ForeignKey("executions.id"), nullable=False)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=True)
    type = Column(String(100), nullable=False) # code_patch, file, report, document
    name = Column(String(255), nullable=False)
    location = Column(String(512), nullable=False)
    metadata_info = Column(JSON, nullable=True, default=dict)
    created_at = Column(DateTime(timezone=True), default=utc_now)


class ExecutionApprovalRequest(Base):
    __tablename__ = "execution_approval_requests"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    execution_id = Column(String(36), ForeignKey("executions.id"), nullable=False)
    node_key = Column(String(255), nullable=True)
    request_type = Column(String(50), nullable=False) # NODE_APPROVAL, TOOL_EXECUTION
    tool_name = Column(String(255), nullable=True)
    tool_args = Column(JSON, nullable=True, default=dict)
    status = Column(String(50), nullable=False, default="PENDING") # PENDING, APPROVED, REJECTED
    reviewer_feedback = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
