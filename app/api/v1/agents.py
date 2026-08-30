from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.services.agent_service import AgentService
from app.schemas.agent import AgentCreate, AgentResponse, AgentVersionCreate, AgentVersionResponse

router = APIRouter(prefix="/agents", tags=["Agents"])

@router.post("", response_model=AgentResponse)
def create_agent(payload: AgentCreate, db: Session = Depends(get_db)):
    service = AgentService(db)
    return service.create_agent(payload)

@router.get("", response_model=List[AgentResponse])
def list_agents(db: Session = Depends(get_db)):
    service = AgentService(db)
    return service.list_agents()

@router.get("/{agent_id}", response_model=AgentResponse)
def get_agent(agent_id: str, db: Session = Depends(get_db)):
    service = AgentService(db)
    agent = service.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found.")
    return agent

@router.post("/{agent_id}/versions", response_model=AgentVersionResponse)
def publish_agent_version(agent_id: str, payload: AgentVersionCreate, db: Session = Depends(get_db)):
    service = AgentService(db)
    agent = service.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found.")
    return service.publish_new_version(agent_id, payload)
