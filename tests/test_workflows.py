import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.db import Base
from app.models.projects import Project
from app.services.agent_service import AgentService
from app.services.workflow_service import WorkflowService
from app.schemas.agent import AgentCreate, AgentVersionCreate
from app.schemas.workflow import (
    WorkflowCreate,
    WorkflowVersionCreate,
    WorkflowNodeCreate,
    WorkflowEdgeCreate,
    WorkflowAgentBindingCreate
)
from app.runtime.workflow_executor import StaticWorkflowExecutor

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def test_workflow_creation_and_execution(db_session):
    # 1. Setup Agents
    agent_svc = AgentService(db_session)
    planner = agent_svc.create_agent(
        AgentCreate(
            name="Planner Agent",
            role="Planner",
            initial_version=AgentVersionCreate(system_prompt="Create task breakdown.", model_provider="mock", model_name="mock-model")
        )
    )
    coder = agent_svc.create_agent(
        AgentCreate(
            name="Coder Agent",
            role="Coder",
            initial_version=AgentVersionCreate(system_prompt="Write code implementation.", model_provider="mock", model_name="mock-model")
        )
    )

    # 2. Setup Project
    proj = Project(name="Workflow Multi-Agent Project")
    db_session.add(proj)
    db_session.commit()

    # 3. Create Workflow & Version
    wf_svc = WorkflowService(db_session)
    version_payload = WorkflowVersionCreate(
        nodes=[
            WorkflowNodeCreate(node_key="planner_node", node_type="agent", agent_id=planner.id),
            WorkflowNodeCreate(node_key="coder_node", node_type="agent", agent_id=coder.id)
        ],
        edges=[
            WorkflowEdgeCreate(source_node_key="planner_node", target_node_key="coder_node"),
            WorkflowEdgeCreate(source_node_key="coder_node", target_node_key="END")
        ],
        agent_bindings=[
            WorkflowAgentBindingCreate(agent_id=planner.id, role="Planner", prompt_overlay="Focus on architecture specification."),
            WorkflowAgentBindingCreate(agent_id=coder.id, role="Coder", prompt_overlay="Focus on clean python code.")
        ]
    )

    wf = wf_svc.create_workflow(
        WorkflowCreate(
            name="Code Generation Workflow",
            description="Planner -> Coder pipeline",
            initial_version=version_payload
        )
    )
    assert wf.id is not None
    assert wf.active_version_id is not None

    # 4. Execute Workflow
    executor = StaticWorkflowExecutor(db_session)
    exec_record = executor.execute(
        workflow_id=wf.id,
        task="Build a REST API feature",
        project_id=proj.id
    )

    assert exec_record.status == "COMPLETED"
    assert exec_record.type == "STATIC_WORKFLOW"
    assert "planner_node" in exec_record.output_data["results"]
    assert "coder_node" in exec_record.output_data["results"]

    # 5. Checkpoints Verification
    checkpoints = wf_svc.get_execution_checkpoints(exec_record.id)
    assert len(checkpoints) == 2
    assert checkpoints[0].node_key == "planner_node"
    assert checkpoints[1].node_key == "coder_node"
