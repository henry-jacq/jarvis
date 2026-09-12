from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from app.core.db import get_db
from app.models.security import AuditEvent

router = APIRouter(prefix="/audit", tags=["Audit & Security"])

class AuditEventResponse(BaseModel):
    id: str
    actor: str
    action: str
    agent_id: Optional[str]
    project_id: Optional[str]
    execution_id: Optional[str]
    tool_name: Optional[str]
    decision: str
    details: Optional[dict]
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)

@router.get("", response_model=List[AuditEventResponse])
def list_audit_events(
    action: Optional[str] = Query(None, description="Filter by audit action"),
    decision: Optional[str] = Query(None, description="Filter by decision (ALLOW, DENY, REVIEW)"),
    execution_id: Optional[str] = Query(None, description="Filter by execution ID"),
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db)
):
    query = db.query(AuditEvent)
    if action:
        query = query.filter(AuditEvent.action == action)
    if decision:
        query = query.filter(AuditEvent.decision == decision)
    if execution_id:
        query = query.filter(AuditEvent.execution_id == execution_id)
    if project_id:
        query = query.filter(AuditEvent.project_id == project_id)

    return query.order_by(AuditEvent.timestamp.desc()).limit(limit).all()
