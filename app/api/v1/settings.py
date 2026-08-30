from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.services.settings_service import SettingsService
from app.schemas.setting import AppSettingCreate, AppSettingResponse

router = APIRouter(prefix="/settings", tags=["App Settings"])

@router.post("", response_model=AppSettingResponse)
def create_or_update_setting(payload: AppSettingCreate, db: Session = Depends(get_db)):
    service = SettingsService(db)
    return service.set_setting(payload)

@router.get("", response_model=List[AppSettingResponse])
def list_settings(category: Optional[str] = None, db: Session = Depends(get_db)):
    service = SettingsService(db)
    return service.list_settings(category=category)

@router.get("/{key}", response_model=AppSettingResponse)
def get_setting(key: str, db: Session = Depends(get_db)):
    service = SettingsService(db)
    setting = service.get_setting(key)
    if not setting:
        raise HTTPException(status_code=404, detail=f"Setting '{key}' not found.")
    return setting
