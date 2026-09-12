import time
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session

from app.models.executions import Execution, ExecutionEvent
from app.models.workflows import WorkflowNode, WorkflowEdge, WorkflowAgentBinding
from app.services.workflow_service import WorkflowService
from app.services.agent_service import AgentService
from app.services.project_service import ProjectService
from app.services.context_builder import ContextBuilder
from app.services.tool_registry import ToolRegistry
from app.runtime.workflow_compiler import WorkflowCompiler
from app.runtime.llm import UnifiedLLMProvider

class StaticWorkflowExecutor:
    """
    Multi-Agent Static & Dynamic LangGraph Workflow Execution Engine.
    Executes compiled multi-agent workflows, evaluates conditional edge expressions,
    handles Human-in-the-Loop (HITL) node interrupts, checkpoints node states,
    and resumes paused executions on user approval.
    """

    def __init__(self, db: Session):
        self.db = db
        self.workflow_service = WorkflowService(db)
        self.agent_service = AgentService(db)
        self.project_service = ProjectService(db)
        self.context_builder = ContextBuilder(db)
        self.tool_registry = ToolRegistry(db)
        self.compiler = WorkflowCompiler()

    def execute(
        self,
        workflow_id: str,
        task: str,
        project_id: Optional[str] = None,
        override_config: Optional[Dict[str, Any]] = None,
        parent_execution_id: Optional[str] = None
    ) -> Execution:
        start_time = time.time()

        # 1. Resolve Workflow & Active Version
        wf = self.workflow_service.get_workflow(workflow_id)
        if not wf:
            raise ValueError(f"Workflow '{workflow_id}' not found.")
        
        ver = self.workflow_service.get_active_version(workflow_id)
        if not ver:
            raise ValueError(f"Workflow '{wf.name}' has no active published version.")

        v_details = self.workflow_service.get_version_details(ver.id)
        nodes: List[WorkflowNode] = v_details["nodes"]
        edges: List[WorkflowEdge] = v_details["edges"]

        # Validate graph
        val_result = self.compiler.validate_graph(nodes, edges)

        # Resolve Project
        project = self.project_service.get_project(project_id) if project_id else None

        # 2. Create Execution Record in DB
        execution = Execution(
            parent_execution_id=parent_execution_id,
            type="STATIC_WORKFLOW",
            project_id=project.id if project else None,
            input_data={"task": task, "workflow_id": wf.id, "version": ver.version},
            status="RUNNING",
            started_at=datetime.now(timezone.utc)
        )
        self.db.add(execution)
        self.db.commit()
        self.db.refresh(execution)

        self._record_event(execution.id, "workflow_started", {"workflow_name": wf.name, "version": ver.version})

        node_map = {n.node_key: n for n in nodes}
        edge_map: Dict[str, List[WorkflowEdge]] = {}
        for e in edges:
            edge_map.setdefault(e.source_node_key, []).append(e)

        current_node_key = val_result["entry_node_key"]
        state_dict: Dict[str, Any] = {"task": task, "results": {}, "node_history": []}

        return self._run_execution_loop(execution, wf, ver, node_map, edge_map, current_node_key, state_dict, start_time)

    def _run_execution_loop(
        self,
        execution: Execution,
        wf: Any,
        ver: Any,
        node_map: Dict[str, WorkflowNode],
        edge_map: Dict[str, List[WorkflowEdge]],
        current_node_key: Optional[str],
        state_dict: Dict[str, Any],
        start_time: float = None
    ) -> Execution:
        if start_time is None:
            start_time = time.time()

        v_details = self.workflow_service.get_version_details(ver.id)
        bindings: List[WorkflowAgentBinding] = v_details["bindings"]
        binding_map = {b.agent_id: b for b in bindings}

        project = self.project_service.get_project(execution.project_id) if execution.project_id else None
        task = state_dict.get("task", "")

        total_input_tokens = execution.input_tokens or 0
        total_output_tokens = execution.output_tokens or 0

        try:
            visited_count = len(state_dict.get("node_history", []))
            max_nodes = 20 # Circuit breaker

            while current_node_key and current_node_key != "END" and visited_count < max_nodes:
                visited_count += 1
                node = node_map.get(current_node_key)
                if not node:
                    break

                self._record_event(execution.id, "workflow_node_started", {"node_key": current_node_key, "node_type": node.node_type})

                node_result_text = ""

                # Handle Human-in-the-Loop approval interrupt
                if node.node_type == "human_approval":
                    approval = self.workflow_service.create_approval_request(
                        execution_id=execution.id,
                        node_key=current_node_key,
                        request_type="NODE_APPROVAL"
                    )
                    execution.status = "WAITING_FOR_APPROVAL"
                    execution.output_data = state_dict
                    
                    self.workflow_service.create_checkpoint(
                        execution_id=execution.id,
                        node_key=current_node_key,
                        state_snapshot={"node_key": current_node_key, "state": state_dict, "approval_id": approval.id}
                    )
                    self._record_event(execution.id, "human_approval_required", {"node_key": current_node_key, "approval_id": approval.id})
                    self.db.commit()
                    self.db.refresh(execution)
                    return execution

                # Execute Agent Node
                elif node.node_type == "agent" and node.agent_id:
                    agent = self.agent_service.get_agent(node.agent_id)
                    agent_ver = self.agent_service.get_active_version(agent) if agent else None

                    if agent and agent_ver:
                        # Apply binding overlays
                        system_prompt = agent_ver.system_prompt
                        binding = binding_map.get(agent.id)
                        if binding and binding.prompt_overlay:
                            system_prompt += f"\n\n[WORKFLOW OVERLAY INSTRUCTIONS]\n{binding.prompt_overlay}"

                        # Build node-specific Context
                        node_task = f"Execute workflow node '{current_node_key}'. Initial Task: {task}\nPrior Node Results: {json.dumps(state_dict['results'])}"
                        exec_ctx = self.context_builder.build_context(
                            task=node_task,
                            agent=agent,
                            agent_version=agent_ver,
                            project=project
                        )

                        # Generate LLM response
                        provider = UnifiedLLMProvider(
                            provider=agent_ver.model_provider,
                            model_name=agent_ver.model_name,
                            temperature=agent_ver.temperature
                        )
                        res = provider.generate(prompt=exec_ctx.composed_prompt, system_prompt=system_prompt)
                        
                        node_result_text = res.get("text", "")
                        total_input_tokens += res.get("input_tokens", 0)
                        total_output_tokens += res.get("output_tokens", 0)

                elif node.node_type == "tool":
                    node_result_text = f"Tool node '{current_node_key}' executed."

                state_dict["results"][current_node_key] = node_result_text
                state_dict["node_history"].append(current_node_key)

                # Save Checkpoint
                self.workflow_service.create_checkpoint(
                    execution_id=execution.id,
                    node_key=current_node_key,
                    state_snapshot={"node_key": current_node_key, "result": node_result_text, "state": state_dict}
                )

                self._record_event(execution.id, "workflow_node_completed", {"node_key": current_node_key})

                # Determine Next Node from Edges using condition evaluation
                outgoing = edge_map.get(current_node_key, [])
                current_node_key = self._select_next_node(outgoing, state_dict)

            execution.status = "COMPLETED"
            execution.output_data = state_dict
            execution.input_tokens = total_input_tokens
            execution.output_tokens = total_output_tokens
            execution.total_tokens = total_input_tokens + total_output_tokens

        except Exception as e:
            execution.status = "FAILED"
            execution.error_message = str(e)
            self._record_event(execution.id, "workflow_error", {"error": str(e)})

        execution.execution_time_ms = round((time.time() - start_time) * 1000, 2)
        execution.completed_at = datetime.now(timezone.utc)
        
        self.db.commit()
        self.db.refresh(execution)
        return execution

    def resume_execution(
        self,
        execution_id: str,
        approval_id: str,
        decision: str,
        feedback: Optional[str] = None
    ) -> Execution:
        execution = self.db.query(Execution).filter(Execution.id == execution_id).first()
        if not execution:
            raise ValueError(f"Execution '{execution_id}' not found.")

        approval = self.workflow_service.resolve_approval_request(approval_id, decision, feedback)

        if decision.upper() == "REJECTED":
            execution.status = "CANCELLED"
            execution.error_message = f"Execution rejected by reviewer. Feedback: {feedback or 'None'}"
            self._record_event(execution.id, "workflow_rejected", {"approval_id": approval_id, "feedback": feedback})
            self.db.commit()
            self.db.refresh(execution)
            return execution

        # Decision APPROVED -> Load latest checkpoint
        checkpoints = self.workflow_service.get_execution_checkpoints(execution_id)
        if not checkpoints:
            raise ValueError(f"No execution checkpoint found to resume execution '{execution_id}'.")

        latest_chk = checkpoints[-1]
        state_dict = latest_chk.state_snapshot.get("state", execution.output_data or {"results": {}, "node_history": []})
        current_node_key = latest_chk.node_key

        execution.status = "RUNNING"
        self._record_event(execution.id, "workflow_resumed", {"approval_id": approval_id, "node_key": current_node_key})

        # Fetch workflow graph structure
        wf_id = execution.input_data.get("workflow_id")
        wf = self.workflow_service.get_workflow(wf_id)
        ver = self.workflow_service.get_active_version(wf_id)
        v_details = self.workflow_service.get_version_details(ver.id)
        nodes: List[WorkflowNode] = v_details["nodes"]
        edges: List[WorkflowEdge] = v_details["edges"]

        node_map = {n.node_key: n for n in nodes}
        edge_map: Dict[str, List[WorkflowEdge]] = {}
        for e in edges:
            edge_map.setdefault(e.source_node_key, []).append(e)

        # Record approval result in state
        state_dict["results"][current_node_key] = f"Approved by human reviewer. Feedback: {feedback or 'Approved'}"

        # Resume to next node after approval step
        outgoing = edge_map.get(current_node_key, [])
        next_node_key = self._select_next_node(outgoing, state_dict)

        return self._run_execution_loop(execution, wf, ver, node_map, edge_map, next_node_key, state_dict)

    def _select_next_node(self, outgoing_edges: List[WorkflowEdge], state_dict: Dict[str, Any]) -> Optional[str]:
        if not outgoing_edges:
            return None

        for edge in outgoing_edges:
            if not edge.condition_expression:
                return edge.target_node_key
            try:
                # Evaluate expression safely in local scope
                local_scope = {"results": state_dict.get("results", {}), "state": state_dict}
                matched = bool(eval(edge.condition_expression, {"__builtins__": {}}, local_scope))
                if matched:
                    return edge.target_node_key
            except Exception:
                pass

        return outgoing_edges[0].target_node_key

    def _record_event(self, execution_id: str, event_type: str, payload: Dict[str, Any]):
        event = ExecutionEvent(
            execution_id=execution_id,
            event_type=event_type,
            payload=payload
        )
        self.db.add(event)
        self.db.commit()

