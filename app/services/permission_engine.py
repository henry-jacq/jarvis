from typing import Dict, Any, Tuple
from sqlalchemy.orm import Session
from app.models.security import PermissionPolicy, AuditEvent
from app.models.agents import AgentVersion

class PermissionEngine:
    """
    Evaluates tool requests against runtime permission policies outside the LLM.
    Enforces Hard Invariant: LLM instructions never constitute security enforcement.
    """

    def __init__(self, db: Session):
        self.db = db

    def evaluate_tool_request(
        self,
        agent_version: AgentVersion,
        tool_name: str,
        tool_args: Dict[str, Any],
        execution_id: str,
        project_id: str = None
    ) -> Tuple[str, str]:
        """
        Evaluates whether a tool invocation is ALLOWED, DENIED, or requires REVIEW.
        Returns (decision, reason).
        """
        tool_policy = agent_version.tool_policy or {}
        allowed = tool_policy.get("allowed", [])
        denied = tool_policy.get("denied", [])
        requires_approval = tool_policy.get("requires_approval", [])

        decision = "ALLOW"
        reason = "Tool request matches allowed agent policy."

        # Hard Deny Check
        if tool_name in denied or "*" in denied:
            decision = "DENY"
            reason = f"Tool '{tool_name}' is explicitly denied by agent security policy."
        elif tool_name in requires_approval:
            decision = "REVIEW"
            reason = f"Tool '{tool_name}' requires human approval before execution."
        elif allowed and (tool_name not in allowed and "*" not in allowed):
            decision = "DENY"
            reason = f"Tool '{tool_name}' is not in allowed tools list {allowed}."

        # Audit event record
        audit_entry = AuditEvent(
            actor=f"agent_version:{agent_version.id}",
            action="tool_permission_evaluated",
            agent_id=agent_version.agent_id,
            project_id=project_id,
            execution_id=execution_id,
            tool_name=tool_name,
            decision=decision,
            details={"args": tool_args, "reason": reason}
        )
        self.db.add(audit_entry)
        self.db.commit()

        return decision, reason
