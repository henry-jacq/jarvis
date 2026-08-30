from typing import Optional, List, Any
from sqlalchemy.orm import Session
from app.models.settings import AppSetting
from app.schemas.setting import AppSettingCreate

class SettingsService:
    def __init__(self, db: Session):
        self.db = db

    def set_setting(self, payload: AppSettingCreate) -> AppSetting:
        existing = self.db.query(AppSetting).filter(AppSetting.key == payload.key).first()
        if existing:
            existing.value = payload.value
            existing.category = payload.category
            existing.data_type = payload.data_type
            existing.description = payload.description
            existing.is_secret = payload.is_secret
            setting_obj = existing
        else:
            setting_obj = AppSetting(
                key=payload.key,
                value=payload.value,
                category=payload.category,
                data_type=payload.data_type,
                description=payload.description,
                is_secret=payload.is_secret
            )
            self.db.add(setting_obj)

        self.db.commit()
        self.db.refresh(setting_obj)
        return setting_obj

    def get_setting(self, key: str) -> Optional[AppSetting]:
        return self.db.query(AppSetting).filter(AppSetting.key == key).first()

    def get_value(self, key: str, default: Any = None) -> Any:
        setting = self.get_setting(key)
        if not setting:
            return default
        val = setting.value
        dtype = setting.data_type.lower()
        if dtype == "integer":
            return int(val)
        elif dtype == "float":
            return float(val)
        elif dtype == "boolean":
            return val.lower() in ["true", "1", "yes"]
        return val

    def list_settings(self, category: Optional[str] = None) -> List[AppSetting]:
        query = self.db.query(AppSetting)
        if category:
            query = query.filter(AppSetting.category == category)
        return query.all()
