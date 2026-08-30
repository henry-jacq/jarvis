import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, JSON, ForeignKey, Integer, Float, Boolean
from app.core.db import Base

def generate_uuid():
    return str(uuid.uuid4())

def utc_now():
    return datetime.now(timezone.utc)

class Job(Base):
    __tablename__ = "jobs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    queue_message_id = Column(String(36), ForeignKey("queue_messages.id"), nullable=True)
    execution_id = Column(String(36), ForeignKey("executions.id"), nullable=True)
    job_type = Column(String(50), nullable=False, default="IMMEDIATE") # IMMEDIATE, SCHEDULED, RECURRING
    
    status = Column(String(50), nullable=False, default="PENDING") # PENDING, QUEUED, RUNNING, COMPLETED, FAILED, CANCELLED
    priority = Column(Integer, nullable=False, default=0)
    
    scheduled_at = Column(DateTime(timezone=True), default=utc_now)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    attempts = Column(Integer, nullable=False, default=0)
    max_attempts = Column(Integer, nullable=False, default=3)
    error = Column(Text, nullable=True)
    metadata_info = Column(JSON, nullable=True, default=dict)
    
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class JobAttempt(Base):
    __tablename__ = "job_attempts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    job_id = Column(String(36), ForeignKey("jobs.id"), nullable=False)
    attempt_number = Column(Integer, nullable=False)
    status = Column(String(50), nullable=False) # SUCCESS, FAILURE
    error_message = Column(Text, nullable=True)
    execution_latency_ms = Column(Float, nullable=False, default=0.0)
    started_at = Column(DateTime(timezone=True), default=utc_now)
    completed_at = Column(DateTime(timezone=True), default=utc_now)


class Schedule(Base):
    __tablename__ = "schedules"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    agent_id = Column(String(36), ForeignKey("agents.id"), nullable=False)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=True)
    
    schedule_expression = Column(String(100), nullable=False) # e.g. "cron:0 9 * * *" or "interval:3600"
    timezone = Column(String(50), nullable=False, default="UTC")
    enabled = Column(Boolean, nullable=False, default=True)
    
    next_run_at = Column(DateTime(timezone=True), nullable=True)
    last_run_at = Column(DateTime(timezone=True), nullable=True)
    task_input = Column(JSON, nullable=False, default=dict)
    
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
