import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, JSON, Boolean
from app.core.db import Base

def generate_uuid():
    return str(uuid.uuid4())

def utc_now():
    return datetime.now(timezone.utc)

class AppSetting(Base):
    __tablename__ = "app_settings"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    key = Column(String(255), nullable=False, unique=True)
    value = Column(Text, nullable=False)
    category = Column(String(100), nullable=False, default="general") # runtime, default_model, memory, security, limits
    data_type = Column(String(50), nullable=False, default="string") # string, integer, float, boolean, json
    description = Column(Text, nullable=True)
    is_secret = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
