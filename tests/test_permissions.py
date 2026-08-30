import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.db import Base
from app.models.agents import AgentVersion
from app.services.permission_engine import PermissionEngine

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def test_permission_engine_allow(db_session):
    agent_ver = AgentVersion(
        id="v1-id",
        agent_id="agent-1",
        version=1,
        system_prompt="Test agent",
        tool_policy={"allowed": ["read_project_file", "git_diff"], "denied": ["delete_file"]}
    )
    db_session.add(agent_ver)
    db_session.commit()

    engine_svc = PermissionEngine(db_session)
    decision, reason = engine_svc.evaluate_tool_request(
        agent_version=agent_ver,
        tool_name="read_project_file",
        tool_args={"file_path": "README.md"},
        execution_id="exec-123"
    )
    assert decision == "ALLOW"

def test_permission_engine_deny(db_session):
    agent_ver = AgentVersion(
        id="v1-id",
        agent_id="agent-1",
        version=1,
        system_prompt="Test agent",
        tool_policy={"allowed": ["read_project_file"], "denied": ["delete_file"]}
    )
    db_session.add(agent_ver)
    db_session.commit()

    engine_svc = PermissionEngine(db_session)
    
    # Denied tool
    decision, reason = engine_svc.evaluate_tool_request(
        agent_version=agent_ver,
        tool_name="delete_file",
        tool_args={"file_path": "important.py"},
        execution_id="exec-123"
    )
    assert decision == "DENY"
    assert "explicitly denied" in reason

    # Tool not in allowed list
    decision, reason = engine_svc.evaluate_tool_request(
        agent_version=agent_ver,
        tool_name="unauthorized_tool",
        tool_args={},
        execution_id="exec-123"
    )
    assert decision == "DENY"
