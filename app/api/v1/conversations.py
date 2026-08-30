from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.services.conversation_service import ConversationService
from app.schemas.conversation import (
    ConversationCreate,
    ConversationResponse,
    MessageCreate,
    MessageResponse,
    ProjectSuggestionResponse
)

router = APIRouter(prefix="/conversations", tags=["Conversations"])

@router.post("", response_model=ConversationResponse)
def create_conversation(payload: ConversationCreate, db: Session = Depends(get_db)):
    service = ConversationService(db)
    return service.create_conversation(payload)

@router.get("/{conversation_id}", response_model=ConversationResponse)
def get_conversation(conversation_id: str, db: Session = Depends(get_db)):
    service = ConversationService(db)
    conv = service.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    conv_dict = ConversationResponse.model_validate(conv)
    conv_dict.messages = [MessageResponse.model_validate(m) for m in service.get_messages(conversation_id)]
    return conv_dict

@router.post("/{conversation_id}/messages", response_model=MessageResponse)
def add_message(conversation_id: str, payload: MessageCreate, db: Session = Depends(get_db)):
    service = ConversationService(db)
    conv = service.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return service.add_message(conversation_id, payload)

@router.get("/{conversation_id}/messages", response_model=List[MessageResponse])
def get_messages(conversation_id: str, limit: int = 50, db: Session = Depends(get_db)):
    service = ConversationService(db)
    return service.get_messages(conversation_id, limit=limit)

@router.post("/{conversation_id}/attach-project/{project_id}", response_model=ConversationResponse)
def attach_to_project(conversation_id: str, project_id: str, db: Session = Depends(get_db)):
    service = ConversationService(db)
    try:
        return service.attach_to_project(conversation_id, project_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/{conversation_id}/suggest-project", response_model=ProjectSuggestionResponse)
def suggest_project(conversation_id: str, db: Session = Depends(get_db)):
    service = ConversationService(db)
    try:
        return service.evaluate_project_suggestion(conversation_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
