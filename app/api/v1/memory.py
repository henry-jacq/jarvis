from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.services.memory_manager import MemoryManager
from app.schemas.memory import MemoryCandidateCreate

router = APIRouter(prefix="/memory", tags=["Memory"])

@router.post("/candidate")
def propose_memory_candidate(payload: MemoryCandidateCreate, db: Session = Depends(get_db)):
    manager = MemoryManager(db)
    try:
        return manager.save_memory_candidate(payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/context")
def retrieve_memory_context(
    scopes: str = "global,agent,project",
    agent_id: Optional[str] = None,
    project_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    manager = MemoryManager(db)
    scope_list = [s.strip().lower() for s in scopes.split(",")]
    return manager.get_memory_for_context(scopes=scope_list, agent_id=agent_id, project_id=project_id)
