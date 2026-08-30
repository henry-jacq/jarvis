import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.db import Base
from app.services.settings_service import SettingsService
from app.schemas.setting import AppSettingCreate

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def test_settings_service_casting(db_session):
    svc = SettingsService(db_session)

    svc.set_setting(AppSettingCreate(key="DEFAULT_MODEL", value="llama3.2", category="model"))
    svc.set_setting(AppSettingCreate(key="DEFAULT_TOKEN_BUDGET", value="8192", category="limits", data_type="integer"))
    svc.set_setting(AppSettingCreate(key="ENABLE_AUDIT", value="true", category="security", data_type="boolean"))

    assert svc.get_value("DEFAULT_MODEL") == "llama3.2"
    assert svc.get_value("DEFAULT_TOKEN_BUDGET") == 8192
    assert svc.get_value("ENABLE_AUDIT") is True
    assert svc.get_value("NON_EXISTENT", default="fallback") == "fallback"
