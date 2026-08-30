import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.db import Base
from app.services.memory_manager import MemoryManager
from app.schemas.memory import MemoryCandidateCreate

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def test_memory_manager_scopes(db_session):
    mm = MemoryManager(db_session)

    # 1. Global Memory candidate
    candidate_g = MemoryCandidateCreate(
        scope="global",
        category="preferences",
        key="theme",
        content="Dark mode preferred",
        importance=0.9
    )
    res_g = mm.save_memory_candidate(candidate_g)
    assert res_g["key"] == "theme"
    assert res_g["scope"] == "global"

    # 2. Agent Memory candidate
    candidate_a = MemoryCandidateCreate(
        scope="agent",
        target_id="agent-100",
        category="learned_insight",
        key="fastapi_pattern",
        content="Use APIRouter prefix parameter for clear modular grouping",
        importance=0.8
    )
    res_a = mm.save_memory_candidate(candidate_a)
    assert res_a["key"] == "fastapi_pattern"
    assert res_a["scope"] == "agent"

    # 3. Retrieve Context
    ctx_mem = mm.get_memory_for_context(scopes=["global", "agent"], agent_id="agent-100")
    assert len(ctx_mem["global"]) == 1
    assert ctx_mem["global"][0]["key"] == "theme"
    assert len(ctx_mem["agent"]) == 1
    assert ctx_mem["agent"][0]["key"] == "fastapi_pattern"
