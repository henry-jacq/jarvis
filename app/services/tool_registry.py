from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from app.models.tools import Tool, ToolVersion
from app.models.agents import AgentVersion
from app.services.permission_engine import PermissionEngine
from app.runtime.tools.builtin import BUILTIN_TOOL_MAP

class ToolRegistry:
    """
    Central tool management and execution service.
    Direct DB access or tool execution by agents is blocked; all invocations pass through
    ToolRegistry and PermissionEngine.
    """

    def __init__(self, db: Session):
        self.db = db
        self.permission_engine = PermissionEngine(db)

    def register_builtin_tools(self):
        """
        Seeds/registers builtin safe tools into the database tool registry if not present.
        """
        for tool_name, tool_info in BUILTIN_TOOL_MAP.items():
            existing = self.db.query(Tool).filter(Tool.name == tool_name).first()
            if not existing:
                tool = Tool(
                    name=tool_name,
                    description=tool_info["description"],
                    input_schema=tool_info["input_schema"],
                    runtime="builtin",
                    risk_level=tool_info["risk_level"],
                    status="active"
                )
                self.db.add(tool)
        self.db.commit()

    def execute_tool(
        self,
        agent_version: AgentVersion,
        tool_name: str,
        tool_args: Dict[str, Any],
        execution_id: str,
        project_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Evaluates permissions via PermissionEngine and invokes the tool if ALLOWED.
        """
        decision, reason = self.permission_engine.evaluate_tool_request(
            agent_version=agent_version,
            tool_name=tool_name,
            tool_args=tool_args,
            execution_id=execution_id,
            project_id=project_id
        )

        if decision != "ALLOW":
            return {
                "status": "denied",
                "decision": decision,
                "reason": reason,
                "tool_name": tool_name
            }

        # Dispatch execution
        if tool_name in BUILTIN_TOOL_MAP:
            tool_fn = BUILTIN_TOOL_MAP[tool_name]["function"]
            try:
                result = tool_fn(**tool_args)
                return {
                    "status": "success",
                    "decision": decision,
                    "result": result,
                    "tool_name": tool_name
                }
            except Exception as e:
                return {
                    "status": "error",
                    "decision": decision,
                    "error": str(e),
                    "tool_name": tool_name
                }
        else:
            return {
                "status": "error",
                "decision": decision,
                "error": f"Tool '{tool_name}' runtime implementation not found.",
                "tool_name": tool_name
            }
