import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, JSON, Integer
from app.core.db import Base

def generate_uuid():
    return str(uuid.uuid4())

def utc_now():
    return datetime.now(timezone.utc)

class QueueMessage(Base):
    """
    Generic Database Queue Table (Primary Queue).
    Decoupled from specific tasks or entity models. Stores generic payloads,
    supports priority sorting, delayed execution, backoff retries, and atomic claiming.
    """
    __tablename__ = "queue_messages"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    topic = Column(String(100), nullable=False, default="default")
    payload_type = Column(String(100), nullable=False) # e.g. agent_execution, scheduled_task, system_event
    payload = Column(JSON, nullable=False, default=dict) # Generic JSON payload
    
    status = Column(String(50), nullable=False, default="PENDING") # PENDING, CLAIMED, PROCESSING, COMPLETED, FAILED, DEAD_LETTER
    priority = Column(Integer, nullable=False, default=0) # Higher integer = higher priority
    attempts = Column(Integer, nullable=False, default=0)
    max_attempts = Column(Integer, nullable=False, default=3)
    
    available_at = Column(DateTime(timezone=True), default=utc_now)
    locked_at = Column(DateTime(timezone=True), nullable=True)
    locked_by = Column(String(255), nullable=True)
    last_error = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
