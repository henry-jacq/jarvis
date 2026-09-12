import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.db import Base
from app.models.projects import Project
from app.services.agent_service import AgentService
from app.services.workflow_service import WorkflowService
from app.services.permission_engine import PermissionEngine
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

def test_hitl_workflow_pause_and_approval_resume(db_session):
    # 1. Setup Agents
    agent_svc = AgentService(db_session)
    planner = agent_svc.create_agent(
        AgentCreate(
            name="Planner Agent",
            role="Planner",
            initial_version=AgentVersionCreate(system_prompt="Break down tasks.", model_provider="mock", model_name="mock-model")
        )
    )

    proj = Project(name="HITL Workflow Project")
    db_session.add(proj)
    db_session.commit()

    # 2. Build Workflow with Human Approval Node: Planner -> Human Approval -> END
    wf_svc = WorkflowService(db_session)
    wf = wf_svc.create_workflow(
        WorkflowCreate(
            name="Human Approval Pipeline",
            description="Workflow requiring human authorization",
            initial_version=WorkflowVersionCreate(
                nodes=[
                    WorkflowNodeCreate(node_key="planner_node", node_type="agent", agent_id=planner.id),
                    WorkflowNodeCreate(node_key="approval_gate", node_type="human_approval")
                ],
                edges=[
                    WorkflowEdgeCreate(source_node_key="planner_node", target_node_key="approval_gate"),
                    WorkflowEdgeCreate(source_node_key="approval_gate", target_node_key="END")
                ],
                agent_bindings=[
                    WorkflowAgentBindingCreate(agent_id=planner.id, role="Planner", prompt_overlay="Propose strategy.")
                ]
            )
        )
    )

    executor = StaticWorkflowExecutor(db_session)
    exec_record = executor.execute(
        workflow_id=wf.id,
        task="Deploy infrastructure change",
        project_id=proj.id
    )

    # 3. Assert execution status is WAITING_FOR_APPROVAL
    assert exec_record.status == "WAITING_FOR_APPROVAL"
    
    pending_approvals = wf_svc.list_pending_approvals()
    assert len(pending_approvals) == 1
    approval = pending_approvals[0]
    assert approval.node_key == "approval_gate"
    assert approval.status == "PENDING"

    # 4. Resume Execution with APPROVED decision
    resumed_exec = executor.resume_execution(
        execution_id=exec_record.id,
        approval_id=approval.id,
        decision="APPROVED",
        feedback="Looks good, proceed to deploy."
    )

    assert resumed_exec.status == "COMPLETED"
    assert "approval_gate" in resumed_exec.output_data["results"]
    assert "Approved by human reviewer" in resumed_exec.output_data["results"]["approval_gate"]

def test_hitl_workflow_rejection(db_session):
    agent_svc = AgentService(db_session)
    planner = agent_svc.create_agent(
        AgentCreate(
            name="Planner Agent",
            role="Planner",
            initial_version=AgentVersionCreate(system_prompt="Plan", model_provider="mock", model_name="mock-model")
        )
    )

    wf_svc = WorkflowService(db_session)
    wf = wf_svc.create_workflow(
        WorkflowCreate(
            name="Rejection Test Pipeline",
            initial_version=WorkflowVersionCreate(
                nodes=[
                    WorkflowNodeCreate(node_key="planner_node", node_type="agent", agent_id=planner.id),
                    WorkflowNodeCreate(node_key="approval_gate", node_type="human_approval")
                ],
                edges=[
                    WorkflowEdgeCreate(source_node_key="planner_node", target_node_key="approval_gate"),
                    WorkflowEdgeCreate(source_node_key="approval_gate", target_node_key="END")
                ],
                agent_bindings=[
                    WorkflowAgentBindingCreate(agent_id=planner.id, role="Planner")
                ]
            )
        )
    )

    executor = StaticWorkflowExecutor(db_session)
    exec_record = executor.execute(workflow_id=wf.id, task="Risky task")
    assert exec_record.status == "WAITING_FOR_APPROVAL"

    pending = wf_svc.list_pending_approvals()[0]
    resumed = executor.resume_execution(
        execution_id=exec_record.id,
        approval_id=pending.id,
        decision="REJECTED",
        feedback="Too risky."
    )

    assert resumed.status == "CANCELLED"
    assert "rejected by reviewer" in resumed.error_message

def test_permission_engine_review_policy(db_session):
    agent_svc = AgentService(db_session)
    agent = agent_svc.create_agent(
        AgentCreate(
            name="Gated Agent",
            role="DevOps",
            initial_version=AgentVersionCreate(
                system_prompt="Deploy code",
                model_provider="mock",
                model_name="mock-model",
                tool_policy={"requires_approval": ["deploy_production"]}
            )
        )
    )
    agent_ver = agent_svc.get_active_version(agent)

    perm_engine = PermissionEngine(db_session)
    decision, reason = perm_engine.evaluate_tool_request(
        agent_version=agent_ver,
        tool_name="deploy_production",
        tool_args={"env": "prod"},
        execution_id="exec-123"
    )

    assert decision == "REVIEW"
    assert "requires human approval" in reason

    wf_svc = WorkflowService(db_session)
    pending = wf_svc.list_pending_approvals()
    assert len(pending) == 1
    assert pending[0].tool_name == "deploy_production"
    assert pending[0].request_type == "TOOL_EXECUTION"
