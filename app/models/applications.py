import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, JSON
from app.core.db import Base

def generate_uuid():
    return str(uuid.uuid4())

def utc_now():
    return datetime.now(timezone.utc)

class Application(Base):
    __tablename__ = "applications"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default="active")
    config = Column(JSON, nullable=True, default=dict)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
