import sys
import os

# Add root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.db import SessionLocal, engine, Base
import app.models
from app.models.applications import Application
from app.models.projects import Project
from app.models.memory import GlobalMemory, ProjectMemory
from app.services.agent_service import AgentService
from app.services.tool_registry import ToolRegistry
from app.schemas.agent import AgentCreate, AgentVersionCreate
from scripts.init_db import ensure_mysql_database_exists

def seed_demo_data():
    ensure_mysql_database_exists()
    db = SessionLocal()
    try:
        # Create DB tables
        Base.metadata.create_all(bind=engine)

        # 1. Register builtin safe tools
        tool_reg = ToolRegistry(db)
        tool_reg.register_builtin_tools()
        print("Builtin tools registered.")

        # 2. Application
        app = db.query(Application).filter(Application.name == "Personal AI Platform").first()
        if not app:
            app = Application(
                name="Personal AI Platform",
                description="Jarvis Core Agent Environment",
                status="active"
            )
            db.add(app)
            db.commit()
            db.refresh(app)
            print(f"Created Application: {app.name} ({app.id})")

        # 3. Project
        proj = db.query(Project).filter(Project.name == "Jarvis Runtime Platform").first()
        if not proj:
            proj = Project(
                application_id=app.id,
                name="Jarvis Runtime Platform",
                description="Secure context-aware agent runtime and orchestration platform.",
                repository="https://github.com/henry/jarvis",
                structured_context={
                    "primary_language": "Python 3.11+",
                    "architecture": "FastAPI + LangGraph + MySQL / SQLite",
                    "database_schema": "Applications, Projects, Agents, Versions, Memory, Executions",
                    "security_policy": "Zero-trust tool execution, Agents cannot directly access DB"
                }
            )
            db.add(proj)
            db.commit()
            db.refresh(proj)
            print(f"Created Project: {proj.name} ({proj.id})")

        # 4. Global & Project Memory
        g_mem = db.query(GlobalMemory).filter(GlobalMemory.key == "user_coding_preference").first()
        if not g_mem:
            g_mem = GlobalMemory(
                application_id=app.id,
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

        # 5. Agent (Coding Agent)
        agent_service = AgentService(db)
        existing_agent = agent_service.list_agents()
        if not existing_agent:
            agent = agent_service.create_agent(
                AgentCreate(
                    name="Coding Agent",
                    role="Senior Full-Stack Engineer",
                    purpose="Analyzes requirements, inspects code files, and proposes high-quality python/fastapi implementations.",
                    application_id=app.id,
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

        print("Demo data seeding completed successfully!")

    finally:
        db.close()

if __name__ == "__main__":
    seed_demo_data()
