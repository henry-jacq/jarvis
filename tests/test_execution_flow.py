import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.db import Base
from app.models.projects import Project
from app.services.agent_service import AgentService
from app.schemas.agent import AgentCreate, AgentVersionCreate
from app.runtime.executor import SimpleAgentExecutor

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def test_simple_agent_executor_flow(db_session):
    proj = Project(name="Project Exec", objective="Test agent execution harness")
    db_session.add(proj)
    db_session.commit()

    agent_svc = AgentService(db_session)
    agent = agent_svc.create_agent(
        AgentCreate(
            name="Mock Agent",
            role="Test Automation Engineer",
            initial_version=AgentVersionCreate(
                system_prompt="Analyze code requirements.",
                model_provider="mock",
                model_name="mock-model",
                tool_policy={"allowed": ["read_project_file"]}
            )
        )
    )

    executor = SimpleAgentExecutor(db_session)
    execution = executor.execute(
        task="Review test coverage",
        agent_id=agent.id,
        project_id=proj.id
    )

    assert execution.status == "COMPLETED"
    assert execution.agent_id == agent.id
    assert execution.project_id == proj.id
    assert execution.output_data is not None
    assert "response" in execution.output_data
    assert execution.total_tokens > 0
