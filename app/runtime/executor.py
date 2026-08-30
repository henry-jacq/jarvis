import time
import json
import re
from datetime import datetime, timezone
from typing import Dict, Any, Optional, TypedDict, List
from sqlalchemy.orm import Session
from langgraph.graph import StateGraph, END

from app.models.executions import Execution, ExecutionEvent
from app.services.agent_service import AgentService
from app.services.project_service import ProjectService
from app.services.context_builder import ContextBuilder, ExecutionContext
from app.services.tool_registry import ToolRegistry
from app.services.memory_manager import MemoryManager
from app.schemas.memory import MemoryCandidateCreate
from app.runtime.llm import UnifiedLLMProvider

class SimpleAgentState(TypedDict):
    execution_id: str
    task: str
    agent_id: str
    project_id: Optional[str]
    context: Optional[Dict[str, Any]]
    composed_prompt: str
    agent_version: Any
    llm_output: Optional[Dict[str, Any]]
    tool_results: List[Dict[str, Any]]
    final_response: str
    status: str
    error: Optional[str]
    input_tokens: int
    output_tokens: int
    total_tokens: int

class SimpleAgentExecutor:
    """
    LangGraph-backed Simple Agent Execution Harness.
    Executes a single agent invocation using structured execution context,
    permission-gated tool execution, token accounting, and memory candidate promotion.
    """

    def __init__(self, db: Session):
        self.db = db
        self.agent_service = AgentService(db)
        self.project_service = ProjectService(db)
        self.context_builder = ContextBuilder(db)
        self.tool_registry = ToolRegistry(db)
        self.memory_manager = MemoryManager(db)

    def execute(
        self,
        task: str,
        agent_id: str,
        project_id: Optional[str] = None,
        override_config: Optional[Dict[str, Any]] = None,
        parent_execution_id: Optional[str] = None
    ) -> Execution:
        start_time = time.time()

        # 1. Resolve Agent & Version
        agent = self.agent_service.get_agent(agent_id)
        if not agent:
            raise ValueError(f"Agent with ID '{agent_id}' not found.")
        
        agent_version = self.agent_service.get_active_version(agent)
        if not agent_version:
            raise ValueError(f"Agent '{agent.name}' has no active version.")

        # 2. Resolve Project
        project = None
        if project_id:
            project = self.project_service.get_project(project_id)
            if not project:
                raise ValueError(f"Project with ID '{project_id}' not found.")

        # 3. Create Execution Record in DB
        execution = Execution(
            parent_execution_id=parent_execution_id,
            type="SIMPLE",
            agent_id=agent.id,
            agent_version_id=agent_version.id,
            project_id=project.id if project else None,
            input_data={"task": task, "override_config": override_config or {}},
            status="RUNNING",
            started_at=datetime.now(timezone.utc)
        )
        self.db.add(execution)
        self.db.commit()
        self.db.refresh(execution)

        # 4. Record Initial Event
        self._record_event(execution.id, "execution_started", {"agent_id": agent.id, "version": agent_version.version})

        # 5. Build Execution Context
        exec_ctx = self.context_builder.build_context(
            task=task,
            agent=agent,
            agent_version=agent_version,
            project=project,
            override_config=override_config
        )
        execution.configuration_snapshot = exec_ctx.to_dict()
        self.db.commit()

        # 6. Build and Run LangGraph Execution Flow
        workflow = StateGraph(SimpleAgentState)

        workflow.add_node("prepare_context", self._node_prepare_context)
        workflow.add_node("call_llm", self._node_call_llm)
        workflow.add_node("process_tools_and_memory", self._node_process_tools_and_memory)

        workflow.set_entry_point("prepare_context")
        workflow.add_edge("prepare_context", "call_llm")
        workflow.add_edge("call_llm", "process_tools_and_memory")
        workflow.add_edge("process_tools_and_memory", END)

        app = workflow.compile()

        initial_state: SimpleAgentState = {
            "execution_id": execution.id,
            "task": task,
            "agent_id": agent.id,
            "project_id": project.id if project else None,
            "context": exec_ctx.to_dict(),
            "composed_prompt": exec_ctx.composed_prompt,
            "agent_version": agent_version,
            "llm_output": None,
            "tool_results": [],
            "final_response": "",
            "status": "RUNNING",
            "error": None,
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0
        }

        try:
            final_state = app.invoke(initial_state)

            execution.status = "COMPLETED"
            execution.output_data = {
                "response": final_state["final_response"],
                "tool_results": final_state["tool_results"]
            }
            execution.input_tokens = final_state["input_tokens"]
            execution.output_tokens = final_state["output_tokens"]
            execution.total_tokens = final_state["total_tokens"]

        except Exception as e:
            execution.status = "FAILED"
            execution.error_message = str(e)
            self._record_event(execution.id, "execution_error", {"error": str(e)})

        execution.execution_time_ms = round((time.time() - start_time) * 1000, 2)
        execution.completed_at = datetime.now(timezone.utc)
        
        self.db.commit()
        self.db.refresh(execution)
        return execution

    def _node_prepare_context(self, state: SimpleAgentState) -> Dict[str, Any]:
        self._record_event(state["execution_id"], "context_prepared", {"composed_prompt_len": len(state["composed_prompt"])})
        return {"status": "CONTEXT_READY"}

    def _node_call_llm(self, state: SimpleAgentState) -> Dict[str, Any]:
        agent_ver = state["agent_version"]
        provider = UnifiedLLMProvider(
            provider=agent_ver.model_provider,
            model_name=agent_ver.model_name,
            temperature=agent_ver.temperature
        )

        self._record_event(state["execution_id"], "llm_call_started", {
            "provider": agent_ver.model_provider,
            "model": agent_ver.model_name
        })

        res = provider.generate(
            prompt=state["composed_prompt"],
            system_prompt=agent_ver.system_prompt
        )

        self._record_event(state["execution_id"], "llm_call_completed", {
            "tokens": res.get("total_tokens", 0)
        })

        return {
            "llm_output": res,
            "final_response": res.get("text", ""),
            "input_tokens": res.get("input_tokens", 0),
            "output_tokens": res.get("output_tokens", 0),
            "total_tokens": res.get("total_tokens", 0)
        }

    def _node_process_tools_and_memory(self, state: SimpleAgentState) -> Dict[str, Any]:
        """
        Parses output for tool execution requests or memory candidate suggestions.
        """
        text = state["final_response"]
        agent_ver = state["agent_version"]
        execution_id = state["execution_id"]
        project_id = state["project_id"]

        tool_results = []
        
        # Look for tool invocation patterns in LLM output, e.g., TOOL: tool_name({"arg": "val"})
        tool_matches = re.findall(r"TOOL:\s*(\w+)\((.*?)\)", text)
        for tool_name, args_raw in tool_matches:
            try:
                args = json.loads(args_raw) if args_raw.strip() else {}
            except Exception:
                args = {}

            self._record_event(execution_id, "tool_requested", {"tool_name": tool_name, "args": args})

            res = self.tool_registry.execute_tool(
                agent_version=agent_ver,
                tool_name=tool_name,
                tool_args=args,
                execution_id=execution_id,
                project_id=project_id
            )

            self._record_event(execution_id, "tool_executed", res)
            tool_results.append(res)

        # Look for memory proposal patterns, e.g. MEMORY: {"scope": "project", "key": "...", "content": "..."}
        memory_matches = re.findall(r"MEMORY:\s*(\{.*?\})", text)
        for mem_raw in memory_matches:
            try:
                mem_data = json.loads(mem_raw)
                target_id = None
                scope = mem_data.get("scope", "global")
                if scope == "agent":
                    target_id = state["agent_id"]
                elif scope == "project":
                    target_id = project_id

                if scope and mem_data.get("key") and mem_data.get("content"):
                    candidate = MemoryCandidateCreate(
                        scope=scope,
                        target_id=target_id,
                        category=mem_data.get("category", "learned_insight"),
                        key=mem_data["key"],
                        content=mem_data["content"],
                        importance=mem_data.get("importance", 1.0),
                        provenance={"execution_id": execution_id}
                    )
                    saved = self.memory_manager.save_memory_candidate(candidate)
                    self._record_event(execution_id, "memory_persisted", saved)
            except Exception as e:
                self._record_event(execution_id, "memory_proposal_error", {"error": str(e)})

        return {"tool_results": tool_results}

    def _record_event(self, execution_id: str, event_type: str, payload: Dict[str, Any]):
        event = ExecutionEvent(
            execution_id=execution_id,
            event_type=event_type,
            payload=payload
        )
        self.db.add(event)
        self.db.commit()
