import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.db import Base
from app.services.queue_service import QueueService
from app.schemas.queue import QueueMessageCreate

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def test_generic_queue_operations(db_session):
    qs = QueueService(db_session)

    # 1. Enqueue generic payload (Decoupled from entity model)
    msg1 = qs.enqueue(
        QueueMessageCreate(
            topic="default",
            payload_type="custom_task",
            payload={"action": "clean_logs", "target_dir": "/tmp/logs"},
            priority=10
        )
    )
    assert msg1.id is not None
    assert msg1.status == "PENDING"
    assert msg1.payload_type == "custom_task"

    msg2 = qs.enqueue(
        QueueMessageCreate(
            topic="default",
            payload_type="agent_execution",
            payload={"task": "Run code review"},
            priority=5
        )
    )

    # 2. Claim next message (Priority 10 claimed first)
    claimed = qs.claim_next_message(worker_id="worker-test-1")
    assert claimed is not None
    assert claimed.id == msg1.id
    assert claimed.status == "CLAIMED"
    assert claimed.locked_by == "worker-test-1"

    # 3. Complete message
    completed = qs.complete_message(claimed.id)
    assert completed.status == "COMPLETED"

    # 4. Claim second message
    claimed2 = qs.claim_next_message(worker_id="worker-test-1")
    assert claimed2.id == msg2.id

    # 5. Fail message (backoff retry)
    failed = qs.fail_message(claimed2.id, "Connection timeout")
    assert failed.status == "PENDING"
    assert failed.attempts == 1
    assert "Connection timeout" in failed.last_error
