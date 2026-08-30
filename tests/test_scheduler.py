import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.db import Base
from app.services.agent_service import AgentService
from app.services.scheduler_service import SchedulerService
from app.schemas.agent import AgentCreate, AgentVersionCreate
from app.schemas.schedule import ScheduleCreate

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def test_scheduler_evaluation(db_session):
    agent_svc = AgentService(db_session)
    agent = agent_svc.create_agent(
        AgentCreate(
            name="Scheduled Agent",
            role="Cron Worker",
            initial_version=AgentVersionCreate(system_prompt="Run cron")
        )
    )

    scheduler = SchedulerService(db_session)

    # 1. Create Schedule
    sched = scheduler.create_schedule(
        ScheduleCreate(
            name="Hourly Health Check",
            agent_id=agent.id,
            schedule_expression="interval:3600",
            task_input={"task": "Run system health check"}
        )
    )
    assert sched.id is not None
    assert sched.enabled is True

    # 2. Force next_run_at to past to simulate due trigger
    sched.next_run_at = datetime.now(timezone.utc) - timedelta(minutes=5)
    db_session.commit()

    # 3. Evaluate schedules
    triggered = scheduler.evaluate_schedules()
    assert len(triggered) == 1
    assert triggered[0]["schedule_id"] == sched.id

    db_session.refresh(sched)
    assert sched.last_run_at is not None
    next_run = sched.next_run_at if sched.next_run_at.tzinfo else sched.next_run_at.replace(tzinfo=timezone.utc)
    assert next_run > datetime.now(timezone.utc)
