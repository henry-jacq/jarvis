from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from app.models.agents import Agent, AgentVersion
from app.models.projects import Project
from app.models.conversations import Conversation, Message
from app.services.memory_manager import MemoryManager
from app.services.settings_service import SettingsService

class ExecutionContext:
    def __init__(
        self,
        task: str,
        system_prompt: str,
        composed_prompt: str,
        agent_info: Dict[str, Any],
        project_info: Optional[Dict[str, Any]],
        memory_context: Dict[str, Any],
        token_budget: int,
        tools_allowed: List[str],
        app_settings: Dict[str, Any]
    ):
        self.task = task
        self.system_prompt = system_prompt
        self.composed_prompt = composed_prompt
        self.agent_info = agent_info
        self.project_info = project_info
        self.memory_context = memory_context
        self.token_budget = token_budget
        self.tools_allowed = tools_allowed
        self.app_settings = app_settings

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task": self.task,
            "system_prompt": self.system_prompt,
            "composed_prompt": self.composed_prompt,
            "agent_info": self.agent_info,
            "project_info": self.project_info,
            "memory_context": self.memory_context,
            "token_budget": self.token_budget,
            "tools_allowed": self.tools_allowed,
            "app_settings": self.app_settings,
        }


class ContextBuilder:
    """
    Trusted platform service that constructs bounded execution context.
    Combines System App Settings, Agent Prompts, Project Workspace Knowledge,
    Persistent Memory, and Task context.
    """

    def __init__(self, db: Session):
        self.db = db
        self.memory_manager = MemoryManager(db)
        self.settings_service = SettingsService(db)

    def build_context(
        self,
        task: str,
        agent: Agent,
        agent_version: AgentVersion,
        project: Optional[Project] = None,
        conversation_id: Optional[str] = None,
        override_config: Optional[Dict[str, Any]] = None
    ) -> ExecutionContext:
        # 1. Fetch App Settings
        settings_list = self.settings_service.list_settings()
        app_settings = {s.key: s.value for s in settings_list if not s.is_secret}

        # 2. Resolve Memory Scopes
        mem_policy = agent_version.memory_policy or {}
        read_scopes = mem_policy.get("read_scopes", ["global", "agent", "project"])
        
        project_id = project.id if project else None
        memory_data = self.memory_manager.get_memory_for_context(
            scopes=read_scopes,
            agent_id=agent.id,
            project_id=project_id
        )

        # 3. Extract Expanded Project Workspace Context
        project_info = None
        if project:
            project_info = {
                "id": project.id,
                "name": project.name,
                "objective": project.objective,
                "repository": project.repository,
                "structured_context": project.structured_context or {},
                "project_settings": project.project_settings or {},
                "project_tasks": project.project_tasks or [],
                "project_documents": project.project_documents or []
            }

        # 4. Layer Prompt Composition
        prompt_layers = [
            f"=== AGENT IDENTITY & ROLE ===",
            f"Agent: {agent.name}",
            f"Role: {agent.role}",
            f"Purpose: {agent.purpose or 'N/A'}\n",
            f"=== INSTRUCTIONS ===",
            agent_version.system_prompt.strip(),
        ]

        if project_info:
            prompt_layers.append(f"\n=== PROJECT WORKSPACE ({project_info['name']}) ===")
            if project_info["objective"]:
                prompt_layers.append(f"Objective: {project_info['objective']}")
            if project_info["repository"]:
                prompt_layers.append(f"Repository: {project_info['repository']}")
            
            struct_ctx = project_info.get("structured_context", {})
            for k, v in struct_ctx.items():
                prompt_layers.append(f"{k}: {v}")

            tasks = project_info.get("project_tasks", [])
            if tasks:
                prompt_layers.append("Active Project Tasks:")
                for t in tasks:
                    status = t.get("status", "pending")
                    prompt_layers.append(f"- [{status.upper()}] {t.get('title', '')}")

        # Add Memory section if memory items exist
        mem_lines = []
        for scope_name, items in memory_data.items():
            if items:
                mem_lines.append(f"[{scope_name.upper()} MEMORY]")
                for item in items:
                    mem_lines.append(f"- {item['key']}: {item['content']}")
        if mem_lines:
            prompt_layers.append("\n=== RELEVANT PERSISTENT MEMORY ===")
            prompt_layers.extend(mem_lines)

        # Add Conversation history if provided
        if conversation_id:
            msgs = self.db.query(Message).filter(
                Message.conversation_id == conversation_id
            ).order_by(Message.created_at.asc()).limit(10).all()
            if msgs:
                prompt_layers.append("\n=== RECENT CONVERSATION HISTORY ===")
                for m in msgs:
                    prompt_layers.append(f"{m.role.upper()}: {m.content}")

        prompt_layers.append(f"\n=== CURRENT TASK ===")
        prompt_layers.append(task.strip())

        composed_prompt = "\n".join(prompt_layers)

        # 5. Resolve Token Budget & Allowed Tools
        ctx_policy = agent_version.context_policy or {}
        token_budget = ctx_policy.get("max_tokens", int(app_settings.get("DEFAULT_TOKEN_BUDGET", 4096)))
        
        tool_pol = agent_version.tool_policy or {}
        tools_allowed = tool_pol.get("allowed", [])

        return ExecutionContext(
            task=task,
            system_prompt=agent_version.system_prompt,
            composed_prompt=composed_prompt,
            agent_info={"id": agent.id, "name": agent.name, "role": agent.role, "version": agent_version.version},
            project_info=project_info,
            memory_context=memory_data,
            token_budget=token_budget,
            tools_allowed=tools_allowed,
            app_settings=app_settings
        )
