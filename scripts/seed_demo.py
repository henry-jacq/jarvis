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

        # 6. Agent (Coding Agent)
        agent_service = AgentService(db)
        existing_agents = agent_service.list_agents()
        agent = existing_agents[0] if existing_agents else None
        if not agent:
            agent = agent_service.create_agent(
                AgentCreate(
                    name="Coding Agent",
                    role="Senior Full-Stack Engineer",
                    purpose="Analyzes requirements, inspects code files, and proposes high-quality implementations.",
                    initial_version=AgentVersionCreate(
                        system_prompt=(
                            "You are a Senior Full-Stack Engineer agent running inside the Jarvis Agent Platform. "
                            "You inspect requirements and project files using approved tools. "
                            "Follow project architecture decisions and coding conventions strictly."
                        ),
                        model_provider="mock",
                        model_name="llama3.2",
                        temperature=0.2,
                        tool_policy={
                            "allowed": ["read_project_file", "git_diff", "list_directory"],
                            "denied": ["delete_database", "deploy_production"]
                        },
                        memory_policy={
                            "read_scopes": ["global", "agent", "project"],
                            "write": True
                        },
                        context_policy={"max_tokens": 4096}
                    )
                )
            )
            print(f"Created Agent: {agent.name} ({agent.id})")

        # 7. Job & Schedule
        job_mgr = JobManager(db)
        demo_job = job_mgr.submit_job(
            JobCreate(
                task="Perform background code quality check",
                agent_id=agent.id,
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
                    agent_id=agent.id,
                    project_id=proj.id,
                    schedule_expression="interval:86400",
                    task_input={"task": "Run daily automated project analysis"}
                )
            )
            print(f"Created Recurring Schedule: {sched.name} ({sched.id})")

        print("Phase 2 Demo data seeding completed successfully!")

    finally:
        db.close()

if __name__ == "__main__":
    seed_demo_data()
