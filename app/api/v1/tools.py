from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.models.tools import Tool
from app.schemas.tool import ToolResponse

router = APIRouter(prefix="/tools", tags=["Tools"])

@router.get("", response_model=List[ToolResponse])
def list_tools(db: Session = Depends(get_db)):
    return db.query(Tool).all()

@router.get("/{tool_id}", response_model=ToolResponse)
def get_tool(tool_id: str, db: Session = Depends(get_db)):
    tool = db.query(Tool).filter(Tool.id == tool_id).first()
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found.")
    return tool
