import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, JSON, ForeignKey, Integer
from app.core.db import Base

def generate_uuid():
    return str(uuid.uuid4())

def utc_now():
    return datetime.now(timezone.utc)

class Workflow(Base):
    __tablename__ = "workflows"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default="DRAFT") # DRAFT, VALIDATED, COMPILED, PUBLISHED, ACTIVE, DEPRECATED
    active_version_id = Column(String(36), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class WorkflowVersion(Base):
    __tablename__ = "workflow_versions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    workflow_id = Column(String(36), ForeignKey("workflows.id"), nullable=False)
    version = Column(Integer, nullable=False)
    input_schema = Column(JSON, nullable=False, default=dict)
    output_schema = Column(JSON, nullable=False, default=dict)
    state_schema = Column(JSON, nullable=False, default=dict)
    config = Column(JSON, nullable=True, default=dict)
    published_at = Column(DateTime(timezone=True), default=utc_now)


class WorkflowNode(Base):
    __tablename__ = "workflow_nodes"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    workflow_version_id = Column(String(36), ForeignKey("workflow_versions.id"), nullable=False)
    node_key = Column(String(100), nullable=False) # e.g. "planner", "coder", "reviewer"
    node_type = Column(String(50), nullable=False, default="agent") # agent, tool, condition, human_approval, sub_workflow
    agent_id = Column(String(36), ForeignKey("agents.id"), nullable=True)
    prompt_overlay = Column(Text, nullable=True)
    config_override = Column(JSON, nullable=True, default=dict)
    input_mapping = Column(JSON, nullable=True, default=dict)
    output_mapping = Column(JSON, nullable=True, default=dict)


class WorkflowEdge(Base):
    __tablename__ = "workflow_edges"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    workflow_version_id = Column(String(36), ForeignKey("workflow_versions.id"), nullable=False)
    source_node_key = Column(String(100), nullable=False)
    target_node_key = Column(String(100), nullable=False)
    condition_expression = Column(Text, nullable=True) # None = unconditional, or Python expression e.g. "review_passed == True"


class WorkflowAgentBinding(Base):
    __tablename__ = "workflow_agent_bindings"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    workflow_id = Column(String(36), ForeignKey("workflows.id"), nullable=False)
    workflow_version_id = Column(String(36), ForeignKey("workflow_versions.id"), nullable=False)
    agent_id = Column(String(36), ForeignKey("agents.id"), nullable=False)
    role = Column(String(255), nullable=False)
    prompt_overlay = Column(Text, nullable=True)
    context_policy = Column(JSON, nullable=True, default=dict)
    tool_policy = Column(JSON, nullable=True, default=dict)
    config_override = Column(JSON, nullable=True, default=dict)


class ExecutionCheckpoint(Base):
    __tablename__ = "execution_checkpoints"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    execution_id = Column(String(36), ForeignKey("executions.id"), nullable=False)
    checkpoint_key = Column(String(100), nullable=False)
    node_key = Column(String(100), nullable=False)
    state_snapshot = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), default=utc_now)
