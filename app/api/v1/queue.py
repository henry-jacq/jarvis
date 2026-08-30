from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.services.queue_service import QueueService
from app.schemas.queue import QueueMessageCreate, QueueMessageResponse
from app.models.queue import QueueMessage

router = APIRouter(prefix="/queue", tags=["Queue"])

@router.post("/enqueue", response_model=QueueMessageResponse)
def enqueue_message(payload: QueueMessageCreate, db: Session = Depends(get_db)):
    service = QueueService(db)
    return service.enqueue(payload)

@router.get("/status")
def get_queue_status(db: Session = Depends(get_db)):
    service = QueueService(db)
    return service.get_queue_status()

@router.get("/messages", response_model=List[QueueMessageResponse])
def list_queue_messages(status: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(QueueMessage)
    if status:
        query = query.filter(QueueMessage.status == status)
    return query.order_by(QueueMessage.created_at.desc()).all()
