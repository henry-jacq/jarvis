import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.db import Base
from app.models.applications import Application
from app.models.projects import Project
from app.models.agents import Agent, AgentVersion
from app.models.memory import GlobalMemory, ProjectMemory
from app.services.context_builder import ContextBuilder

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def test_context_builder_assembly(db_session):
    app = Application(name="App1", description="Test Application")
    db_session.add(app)
    db_session.commit()

    proj = Project(
        application_id=app.id,
        name="Jarvis Test Project",
        structured_context={"primary_language": "Python 3.11", "framework": "FastAPI"}
    )
    db_session.add(proj)
    
    agent = Agent(name="Tester Agent", role="Quality Engineer")
    db_session.add(agent)
    db_session.commit()

    ver = AgentVersion(
        agent_id=agent.id,
        version=1,
        system_prompt="Always write unit tests for every endpoint.",
        tool_policy={"allowed": ["read_project_file"]},
        memory_policy={"read_scopes": ["global", "project"], "write": True}
    )
    db_session.add(ver)
    agent.active_version_id = ver.id

    g_mem = GlobalMemory(key="global_rule", content="Use clear variable names.")
    p_mem = ProjectMemory(project_id=proj.id, key="project_rule", content="Follow standard REST conventions.")
    db_session.add_all([g_mem, p_mem])
    db_session.commit()

    cb = ContextBuilder(db_session)
    exec_ctx = cb.build_context(
        task="Write tests for Application router",
        agent=agent,
        agent_version=ver,
        project=proj
    )

    prompt = exec_ctx.composed_prompt
    assert "Tester Agent" in prompt
    assert "Always write unit tests for every endpoint." in prompt
    assert "Jarvis Test Project" in prompt
    assert "primary_language: Python 3.11" in prompt
    assert "global_rule: Use clear variable names." in prompt
    assert "project_rule: Follow standard REST conventions." in prompt
    assert "Write tests for Application router" in prompt
