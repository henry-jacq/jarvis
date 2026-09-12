from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.workflows import (
    Workflow,
    WorkflowVersion,
    WorkflowNode,
    WorkflowEdge,
    WorkflowAgentBinding,
    ExecutionCheckpoint
)
from app.models.executions import ExecutionApprovalRequest
from app.schemas.workflow import WorkflowCreate, WorkflowVersionCreate

class WorkflowService:
    def __init__(self, db: Session):
        self.db = db

    def create_workflow(self, payload: WorkflowCreate) -> Workflow:
        wf = Workflow(
            name=payload.name,
            description=payload.description,
            status="DRAFT"
        )
        self.db.add(wf)
        self.db.commit()
        self.db.refresh(wf)

        # Publish initial version v1
        ver = self.publish_version(wf.id, payload.initial_version)
        wf.status = "PUBLISHED"
        wf.active_version_id = ver.id
        self.db.commit()
        self.db.refresh(wf)
        return wf

    def publish_version(self, workflow_id: str, payload: WorkflowVersionCreate) -> WorkflowVersion:
        latest = self.db.query(WorkflowVersion).filter(
            WorkflowVersion.workflow_id == workflow_id
        ).order_by(WorkflowVersion.version.desc()).first()

        next_ver = (latest.version + 1) if latest else 1

        ver = WorkflowVersion(
            workflow_id=workflow_id,
            version=next_ver,
            input_schema=payload.input_schema,
            output_schema=payload.output_schema,
            state_schema=payload.state_schema,
            config=payload.config or {}
        )
        self.db.add(ver)
        self.db.commit()
        self.db.refresh(ver)

        # Add Nodes
        for n in payload.nodes:
            node = WorkflowNode(
                workflow_version_id=ver.id,
                node_key=n.node_key,
                node_type=n.node_type,
                agent_id=n.agent_id,
                prompt_overlay=n.prompt_overlay,
                config_override=n.config_override or {},
                input_mapping=n.input_mapping or {},
                output_mapping=n.output_mapping or {}
            )
            self.db.add(node)

        # Add Edges
        for e in payload.edges:
            edge = WorkflowEdge(
                workflow_version_id=ver.id,
                source_node_key=e.source_node_key,
                target_node_key=e.target_node_key,
                condition_expression=e.condition_expression
            )
            self.db.add(edge)

        # Add Agent Bindings
        for b in payload.agent_bindings:
            binding = WorkflowAgentBinding(
                workflow_id=workflow_id,
                workflow_version_id=ver.id,
                agent_id=b.agent_id,
                role=b.role,
                prompt_overlay=b.prompt_overlay,
                context_policy=b.context_policy or {},
                tool_policy=b.tool_policy or {},
                config_override=b.config_override or {}
            )
            self.db.add(binding)

        self.db.commit()
        self.db.refresh(ver)

        # Update active version on workflow
        wf = self.db.query(Workflow).filter(Workflow.id == workflow_id).first()
        if wf:
            wf.active_version_id = ver.id
            wf.status = "PUBLISHED"
            self.db.commit()

        return ver

    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        return self.db.query(Workflow).filter(Workflow.id == workflow_id).first()

    def get_active_version(self, workflow_id: str) -> Optional[WorkflowVersion]:
        wf = self.get_workflow(workflow_id)
        if not wf or not wf.active_version_id:
            return None
        return self.db.query(WorkflowVersion).filter(WorkflowVersion.id == wf.active_version_id).first()

    def get_version_details(self, version_id: str) -> Dict[str, Any]:
        ver = self.db.query(WorkflowVersion).filter(WorkflowVersion.id == version_id).first()
        if not ver:
            raise ValueError(f"Workflow version '{version_id}' not found.")
        nodes = self.db.query(WorkflowNode).filter(WorkflowNode.workflow_version_id == version_id).all()
        edges = self.db.query(WorkflowEdge).filter(WorkflowEdge.workflow_version_id == version_id).all()
        bindings = self.db.query(WorkflowAgentBinding).filter(WorkflowAgentBinding.workflow_version_id == version_id).all()
        return {
            "version": ver,
            "nodes": nodes,
            "edges": edges,
            "bindings": bindings
        }

    def list_workflows(self) -> List[Workflow]:
        return self.db.query(Workflow).all()

    def create_checkpoint(self, execution_id: str, node_key: str, state_snapshot: Dict[str, Any]) -> ExecutionCheckpoint:
        checkpoint_key = f"chk_{node_key}_{int(datetime.now(timezone.utc).timestamp())}"
        chk = ExecutionCheckpoint(
            execution_id=execution_id,
            checkpoint_key=checkpoint_key,
            node_key=node_key,
            state_snapshot=state_snapshot
        )
        self.db.add(chk)
        self.db.commit()
        self.db.refresh(chk)
        return chk

    def get_execution_checkpoints(self, execution_id: str) -> List[ExecutionCheckpoint]:
        return self.db.query(ExecutionCheckpoint).filter(
            ExecutionCheckpoint.execution_id == execution_id
        ).order_by(ExecutionCheckpoint.created_at.asc()).all()

    def create_approval_request(
        self,
        execution_id: str,
        node_key: Optional[str],
        request_type: str = "NODE_APPROVAL",
        tool_name: Optional[str] = None,
        tool_args: Optional[Dict[str, Any]] = None
    ) -> ExecutionApprovalRequest:
        req = ExecutionApprovalRequest(
            execution_id=execution_id,
            node_key=node_key,
            request_type=request_type,
            tool_name=tool_name,
            tool_args=tool_args,
            status="PENDING"
        )
        self.db.add(req)
        self.db.commit()
        self.db.refresh(req)
        return req

    def list_pending_approvals(self) -> List[ExecutionApprovalRequest]:
        return self.db.query(ExecutionApprovalRequest).filter(
            ExecutionApprovalRequest.status == "PENDING"
        ).order_by(ExecutionApprovalRequest.created_at.desc()).all()

    def get_approval_request(self, approval_id: str) -> Optional[ExecutionApprovalRequest]:
        return self.db.query(ExecutionApprovalRequest).filter(
            ExecutionApprovalRequest.id == approval_id
        ).first()

    def resolve_approval_request(
        self,
        approval_id: str,
        decision: str,
        feedback: Optional[str] = None
    ) -> ExecutionApprovalRequest:
        req = self.get_approval_request(approval_id)
        if not req:
            raise ValueError(f"Approval request '{approval_id}' not found.")
        req.status = decision.upper()
        req.reviewer_feedback = feedback
        req.resolved_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(req)
        return req

