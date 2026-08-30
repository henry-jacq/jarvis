from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.models.applications import Application
from app.schemas.application import ApplicationCreate, ApplicationResponse

router = APIRouter(prefix="/applications", tags=["Applications"])

@router.post("", response_model=ApplicationResponse)
def create_application(payload: ApplicationCreate, db: Session = Depends(get_db)):
    existing = db.query(Application).filter(Application.name == payload.name).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Application '{payload.name}' already exists.")
    app = Application(
        name=payload.name,
        description=payload.description,
        status=payload.status,
        config=payload.config or {}
    )
    db.add(app)
    db.commit()
    db.refresh(app)
    return app

@router.get("", response_model=List[ApplicationResponse])
def list_applications(db: Session = Depends(get_db)):
    return db.query(Application).all()

@router.get("/{application_id}", response_model=ApplicationResponse)
def get_application(application_id: str, db: Session = Depends(get_db)):
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found.")
    return app
