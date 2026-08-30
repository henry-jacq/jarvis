from typing import Optional, Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class AppSettingBase(BaseModel):
    key: str
    value: str
    category: str = "general"
    data_type: str = "string"
    description: Optional[str] = None
    is_secret: bool = False

class AppSettingCreate(AppSettingBase):
    pass

class AppSettingResponse(AppSettingBase):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
