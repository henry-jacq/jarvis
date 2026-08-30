import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, JSON, Integer, ForeignKey
from app.core.db import Base

def generate_uuid():
    return str(uuid.uuid4())

def utc_now():
    return datetime.now(timezone.utc)

class Tool(Base):
    __tablename__ = "tools"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=False)
    input_schema = Column(JSON, nullable=False, default=dict)
    output_schema = Column(JSON, nullable=True, default=dict)
    runtime = Column(String(100), nullable=False, default="builtin") # e.g. builtin, python, mcp
    risk_level = Column(String(50), nullable=False, default="LOW") # LOW, MEDIUM, HIGH, CRITICAL
    status = Column(String(50), nullable=False, default="active")
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class ToolVersion(Base):
    __tablename__ = "tool_versions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tool_id = Column(String(36), ForeignKey("tools.id"), nullable=False)
    version = Column(Integer, nullable=False)
    input_schema = Column(JSON, nullable=False, default=dict)
    output_schema = Column(JSON, nullable=True, default=dict)
    code_reference = Column(String(255), nullable=True)
    published_at = Column(DateTime(timezone=True), default=utc_now)
