import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.db import Base
from app.models.projects import Project
from app.models.memory import GlobalMemory, AgentMemory, ProjectMemory
from app.services.agent_service import AgentService
from app.services.workflow_service import WorkflowService
from app.services.job_manager import JobManager
from app.services.memory_manager import MemoryManager
from app.schemas.agent import AgentCreate, AgentVersionCreate
from app.schemas.workflow import (
    WorkflowCreate,
    WorkflowVersionCreate,
    WorkflowNodeCreate,
    WorkflowEdgeCreate,
    WorkflowAgentBindingCreate
)
from app.schemas.job import JobCreate
from app.schemas.memory import MemoryCandidateCreate
from app.runtime.worker import WorkerEngine
from app.runtime.workflow_compiler import WorkflowCompiler

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def test_workflow_job_submission_and_worker_execution(db_session):
    agent_svc = AgentService(db_session)
    agent = agent_svc.create_agent(
        AgentCreate(
            name="Workflow Worker Agent",
            role="Worker",
            initial_version=AgentVersionCreate(system_prompt="Execute background job step.", model_provider="mock", model_name="mock-model")
        )
    )

    wf_svc = WorkflowService(db_session)
    wf = wf_svc.create_workflow(
        WorkflowCreate(
            name="Background Workflow Pipeline",
            initial_version=WorkflowVersionCreate(
                nodes=[
                    WorkflowNodeCreate(node_key="step_1", node_type="agent", agent_id=agent.id)
                ],
                edges=[
                    WorkflowEdgeCreate(source_node_key="step_1", target_node_key="END")
                ],
                agent_bindings=[
                    WorkflowAgentBindingCreate(agent_id=agent.id, role="Worker")
                ]
            )
        )
    )

    job_mgr = JobManager(db_session)
    job = job_mgr.submit_job(
        JobCreate(
            task="Run background workflow job",
            workflow_id=wf.id,
            priority=5
        )
    )
    assert job.status == "QUEUED"

    worker = WorkerEngine(worker_id="worker-phase5")
    processed = worker.process_one_message(db_session)
    assert processed is True

    db_session.refresh(job)
    assert job.status == "COMPLETED"
    assert job.execution_id is not None

    attempts = job_mgr.get_job_attempts(job.id)
    assert len(attempts) == 1
    assert attempts[0].status == "SUCCESS"

def test_memory_decay_min_importance_and_vector_stubs(db_session):
    mem_mgr = MemoryManager(db_session)
    
    mem_mgr.save_memory_candidate(
        MemoryCandidateCreate(
            scope="global",
            category="architecture",
            key="high_priority_rule",
            content="Always enforce zero-trust tool permissions",
            importance=1.0
        )
    )
    mem_mgr.save_memory_candidate(
        MemoryCandidateCreate(
            scope="global",
            category="architecture",
            key="low_priority_rule",
            content="Optional logging format preference",
            importance=0.4
        )
    )

    # Filter with min_importance
    high_importance_mems = mem_mgr.get_memory_for_context(scopes=["global"], min_importance=0.8)
    assert len(high_importance_mems["global"]) == 1
    assert high_importance_mems["global"][0]["key"] == "high_priority_rule"

    # Test Vector search stubs
    stubs = mem_mgr.search_vector_stubs(query="zero-trust permissions", scopes=["global"])
    assert len(stubs) >= 1
    assert stubs[0]["key"] == "high_priority_rule"

    # Test Decay
    mem_mgr.apply_memory_decay(decay_factor=0.5)
    g_rule = db_session.query(GlobalMemory).filter(GlobalMemory.key == "high_priority_rule").first()
    assert g_rule.importance == 0.5

def test_workflow_compiler_max_nodes_limit():
    compiler = WorkflowCompiler()
    nodes = [
        WorkflowNodeCreate(node_key=f"node_{i}", node_type="agent") for i in range(25)
    ]
    edges = [
        WorkflowEdgeCreate(source_node_key=f"node_{i}", target_node_key=f"node_{i+1}") for i in range(24)
    ]
    with pytest.raises(ValueError, match="Workflow exceeds maximum allowed node count"):
        compiler.validate_graph(nodes, edges, max_nodes=20)
