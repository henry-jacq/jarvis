import sys
import os

# Add root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.db import SessionLocal, engine, Base
import app.models
from app.models.projects import Project
from app.models.memory import GlobalMemory, ProjectMemory
from app.services.settings_service import SettingsService
from app.services.agent_service import AgentService
from app.services.conversation_service import ConversationService
from app.services.tool_registry import ToolRegistry
from app.services.job_manager import JobManager
from app.services.scheduler_service import SchedulerService
from app.schemas.setting import AppSettingCreate
from app.schemas.agent import AgentCreate, AgentVersionCreate
from app.schemas.conversation import ConversationCreate, MessageCreate
from app.schemas.job import JobCreate
from app.schemas.schedule import ScheduleCreate
from scripts.init_db import ensure_mysql_database_exists

from app.models.workflows import Workflow
from app.services.workflow_service import WorkflowService
from app.schemas.workflow import (
    WorkflowCreate,
    WorkflowVersionCreate,
    WorkflowNodeCreate,
    WorkflowEdgeCreate,
    WorkflowAgentBindingCreate
)

def seed_demo_data():
    ensure_mysql_database_exists()
    db = SessionLocal()
    try:
        Base.metadata.create_all(bind=engine)

        # 1. Register builtin safe tools
        tool_reg = ToolRegistry(db)
        tool_reg.register_builtin_tools()
        print("Builtin tools registered.")

        # 2. System App Settings
        settings_svc = SettingsService(db)
        settings_svc.set_setting(AppSettingCreate(
            key="DEFAULT_MODEL",
            value="llama3.2",
            category="default_model",
            description="Default LLM model name"
        ))
        settings_svc.set_setting(AppSettingCreate(
            key="DEFAULT_TOKEN_BUDGET",
            value="4096",
            category="limits",
            data_type="integer",
            description="Default execution token budget"
        ))
        settings_svc.set_setting(AppSettingCreate(
            key="MAX_WORKFLOW_DEPTH",
            value="3",
            category="limits",
            data_type="integer",
            description="Maximum nested workflow depth limit"
        ))
        settings_svc.set_setting(AppSettingCreate(
            key="MAX_NODES",
            value="20",
            category="limits",
            data_type="integer",
            description="Maximum workflow node count limit"
        ))
        settings_svc.set_setting(AppSettingCreate(
            key="MAX_PARALLEL_BRANCHES",
            value="5",
            category="limits",
            data_type="integer",
            description="Maximum parallel workflow branch limit"
        ))
        print("System App Settings populated.")

        # 3. Project Workspace
        proj = db.query(Project).filter(Project.name == "Jarvis Runtime Platform").first()
        if not proj:
            proj = Project(
                name="Jarvis Runtime Platform",
                objective="Build a secure, context-aware agent runtime & orchestration platform.",
                description="Self-hosted agent platform running stateless agents over persistent MySQL state.",
                repository="https://github.com/henry/jarvis",
                structured_context={
                    "primary_language": "Python 3.11+",
                    "architecture": "FastAPI + LangGraph + MySQL",
                    "database_schema": "App Settings, Projects, Conversations, Agents, Memory, Executions, Generic Queue, Jobs",
                    "security_policy": "Zero-trust tool execution, Agents cannot directly access DB"
                },
                project_tasks=[
                    {"id": "t1", "title": "Implement App Settings Store", "status": "completed"},
                    {"id": "t2", "title": "Implement Generic Queue & Job Worker", "status": "completed"},
                    {"id": "t3", "title": "Implement LangGraph Simple Agent Harness", "status": "completed"}
                ],
                project_documents=[
                    {"id": "d1", "title": "Architecture Overview", "type": "markdown", "content": "Stateless Agents, Persistent Platform State."}
                ]
            )
            db.add(proj)
            db.commit()
            db.refresh(proj)
            print(f"Created Project Workspace: {proj.name} ({proj.id})")

        # 4. Global & Project Memory
        g_mem = db.query(GlobalMemory).filter(GlobalMemory.key == "user_coding_preference").first()
        if not g_mem:
            g_mem = GlobalMemory(
                category="preferences",
                key="user_coding_preference",
                content="Prefer modular code with explicit type hints and strict error handling.",
                importance=1.0
            )
            db.add(g_mem)

        p_mem = db.query(ProjectMemory).filter(ProjectMemory.project_id == proj.id).first()
        if not p_mem:
            p_mem = ProjectMemory(
                project_id=proj.id,
                category="architecture",
                key="database_access_invariant",
                content="HARD INVARIANT: LLM/Agents never receive raw SQL or DB credentials. Context Builder mediates data access.",
                importance=1.0
            )
            db.add(p_mem)

        db.commit()

        # 5. Conversation
        conv_svc = ConversationService(db)
        conv = conv_svc.create_conversation(
            ConversationCreate(
                title="Jarvis Architecture Discussion",
                project_id=proj.id,
                initial_message=MessageCreate(
                    role="user",
                    content="How do we handle background queues and jobs in Jarvis?"
                )
            )
        )
        conv_svc.add_message(conv.id, MessageCreate(
            role="assistant",
            content="MySQL is the primary durable queue store (queue_messages table) with generic work payloads. Redis is an optional secondary notification dispatch broker."
        ))
        print(f"Created Conversation: {conv.title} ({conv.id})")

        # 6. Specialized Agents for Multi-Agent Workflow
        agent_service = AgentService(db)
        existing_agents = {a.role: a for a in agent_service.list_agents()}

        planner = existing_agents.get("Planner")
        if not planner:
            planner = agent_service.create_agent(
                AgentCreate(
                    name="Planner Agent",
                    role="Planner",
                    purpose="Deconstructs complex tasks into structured technical specifications and subtasks.",
                    initial_version=AgentVersionCreate(
                        system_prompt="You are a Lead Software Architect. Break down incoming requirements into clear implementation steps.",
                        model_provider="mock",
                        model_name="llama3.2"
                    )
                )
            )
            print(f"Created Agent: {planner.name} ({planner.id})")

        coder = existing_agents.get("Coder")
        if not coder:
            coder = agent_service.create_agent(
                AgentCreate(
                    name="Coder Agent",
                    role="Coder",
                    purpose="Generates production-grade code based on technical specifications.",
                    initial_version=AgentVersionCreate(
                        system_prompt="You are a Senior Software Developer. Write clean, robust python code based on prior planner outputs.",
                        model_provider="mock",
                        model_name="llama3.2"
                    )
                )
            )
            print(f"Created Agent: {coder.name} ({coder.id})")

        reviewer = existing_agents.get("Reviewer")
        if not reviewer:
            reviewer = agent_service.create_agent(
                AgentCreate(
                    name="Reviewer Agent",
                    role="Reviewer",
                    purpose="Audits generated code for architecture compliance, security vulnerabilities, and quality.",
                    initial_version=AgentVersionCreate(
                        system_prompt="You are a QA & Security Auditor. Audit code generated by the coder against requirements.",
                        model_provider="mock",
                        model_name="llama3.2"
                    )
                )
            )
            print(f"Created Agent: {reviewer.name} ({reviewer.id})")

        # 7. Multi-Agent Static Workflow
        wf_svc = WorkflowService(db)
        existing_wfs = wf_svc.list_workflows()
        if not existing_wfs:
            demo_wf = wf_svc.create_workflow(
                WorkflowCreate(
                    name="Feature Development Pipeline",
                    description="Multi-agent static workflow: Planner -> Coder -> Reviewer",
                    initial_version=WorkflowVersionCreate(
                        nodes=[
                            WorkflowNodeCreate(node_key="planner_stage", node_type="agent", agent_id=planner.id),
                            WorkflowNodeCreate(node_key="coder_stage", node_type="agent", agent_id=coder.id),
                            WorkflowNodeCreate(node_key="reviewer_stage", node_type="agent", agent_id=reviewer.id)
                        ],
                        edges=[
                            WorkflowEdgeCreate(source_node_key="planner_stage", target_node_key="coder_stage"),
                            WorkflowEdgeCreate(source_node_key="coder_stage", target_node_key="reviewer_stage"),
                            WorkflowEdgeCreate(source_node_key="reviewer_stage", target_node_key="END")
                        ],
                        agent_bindings=[
                            WorkflowAgentBindingCreate(agent_id=planner.id, role="Planner", prompt_overlay="Focus on modular component breakdown."),
                            WorkflowAgentBindingCreate(agent_id=coder.id, role="Coder", prompt_overlay="Ensure typing and error handling."),
                            WorkflowAgentBindingCreate(agent_id=reviewer.id, role="Reviewer", prompt_overlay="Verify security invariants.")
                        ]
                    )
                )
            )
            print(f"Created Multi-Agent Workflow: {demo_wf.name} ({demo_wf.id})")

        # 8. Phase 4 HITL & Dynamic Workflow
        hitl_wf = db.query(Workflow).filter(Workflow.name == "Production Deployment Pipeline").first()
        if not hitl_wf:
            hitl_wf = wf_svc.create_workflow(
                WorkflowCreate(
                    name="Production Deployment Pipeline",
                    description="Dynamic workflow with Human-in-the-Loop approval gate: Planner -> Coder -> Human Approval -> Reviewer",
                    initial_version=WorkflowVersionCreate(
                        nodes=[
                            WorkflowNodeCreate(node_key="planner_stage", node_type="agent", agent_id=planner.id),
                            WorkflowNodeCreate(node_key="coder_stage", node_type="agent", agent_id=coder.id),
                            WorkflowNodeCreate(node_key="human_security_gate", node_type="human_approval"),
                            WorkflowNodeCreate(node_key="reviewer_stage", node_type="agent", agent_id=reviewer.id)
                        ],
                        edges=[
                            WorkflowEdgeCreate(source_node_key="planner_stage", target_node_key="coder_stage"),
                            WorkflowEdgeCreate(source_node_key="coder_stage", target_node_key="human_security_gate"),
                            WorkflowEdgeCreate(source_node_key="human_security_gate", target_node_key="reviewer_stage"),
                            WorkflowEdgeCreate(source_node_key="reviewer_stage", target_node_key="END")
                        ],
                        agent_bindings=[
                            WorkflowAgentBindingCreate(agent_id=planner.id, role="Planner", prompt_overlay="Plan deployment strategy."),
                            WorkflowAgentBindingCreate(agent_id=coder.id, role="Coder", prompt_overlay="Prepare production code."),
                            WorkflowAgentBindingCreate(agent_id=reviewer.id, role="Reviewer", prompt_overlay="Audit deployment result.")
                        ]
                    )
                )
            )
            print(f"Created HITL Dynamic Workflow: {hitl_wf.name} ({hitl_wf.id})")

        # 9. Job & Schedule
        job_mgr = JobManager(db)
        demo_job = job_mgr.submit_job(
            JobCreate(
                task="Perform background code quality check",
                agent_id=coder.id,
                project_id=proj.id,
                priority=10
            )
        )
        print(f"Enqueued Demo Background Job: {demo_job.id}")

        sched_svc = SchedulerService(db)
        existing_scheds = sched_svc.list_schedules()
        if not existing_scheds:
            sched = sched_svc.create_schedule(
                ScheduleCreate(
                    name="Daily Project Inspection",
                    agent_id=coder.id,
                    project_id=proj.id,
                    schedule_expression="interval:86400",
                    task_input={"task": "Run daily automated project analysis"}
                )
            )
            print(f"Created Recurring Schedule: {sched.name} ({sched.id})")

        print("Phase 4 Demo data seeding completed successfully!")

    finally:
        db.close()

if __name__ == "__main__":
    seed_demo_data()


