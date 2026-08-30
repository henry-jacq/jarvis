import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.db import Base
from app.models.projects import Project
from app.services.agent_service import AgentService
from app.services.job_manager import JobManager
from app.schemas.agent import AgentCreate, AgentVersionCreate
from app.schemas.job import JobCreate
from app.runtime.worker import WorkerEngine

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def test_job_submission_and_worker_execution(db_session):
    proj = Project(name="Job Execution Project")
    db_session.add(proj)
    db_session.commit()

    agent_svc = AgentService(db_session)
    agent = agent_svc.create_agent(
        AgentCreate(
            name="Background Agent",
            role="Automation Agent",
            initial_version=AgentVersionCreate(
                system_prompt="Execute background tasks.",
                model_provider="mock",
                model_name="mock-model",
                tool_policy={"allowed": ["read_project_file"]}
            )
        )
    )

    job_mgr = JobManager(db_session)

    # 1. Submit Job
    job = job_mgr.submit_job(
        JobCreate(
            task="Perform automated background inspection",
            agent_id=agent.id,
            project_id=proj.id,
            priority=5
        )
    )
    assert job.id is not None
    assert job.status == "QUEUED"

    # 2. Worker Engine processes queued message
    worker = WorkerEngine(worker_id="worker-test-1")
    processed = worker.process_one_message(db_session)
    assert processed is True

    # 3. Check completed job status and attempt history
    db_session.refresh(job)
    assert job.status == "COMPLETED"
    assert job.execution_id is not None

    attempts = job_mgr.get_job_attempts(job.id)
    assert len(attempts) == 1
    assert attempts[0].status == "SUCCESS"

def test_job_cancellation(db_session):
    agent_svc = AgentService(db_session)
    agent = agent_svc.create_agent(
        AgentCreate(
            name="Cancel Agent",
            role="Worker",
            initial_version=AgentVersionCreate(system_prompt="Test")
        )
    )

    job_mgr = JobManager(db_session)
    job = job_mgr.submit_job(JobCreate(task="Long task", agent_id=agent.id))
    
    cancelled = job_mgr.cancel_job(job.id)
    assert cancelled.status == "CANCELLED"
