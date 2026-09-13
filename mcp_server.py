import sys
import json
import logging
import os

# Add root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from dotenv import load_dotenv
env_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(env_path):
    load_dotenv(env_path)

from app.core.db import SessionLocal

from app.services.agent_service import AgentService
from app.services.workflow_service import WorkflowService
from app.services.project_service import ProjectService
from app.services.job_manager import JobManager
from app.services.queue_service import QueueService
from app.services.memory_manager import MemoryManager
from app.runtime.executor import SimpleAgentExecutor
from app.runtime.workflow_executor import StaticWorkflowExecutor
from app.schemas.job import JobCreate
from app.schemas.memory import MemoryCandidateCreate
from app.models.security import AuditEvent

logging.basicConfig(level=logging.ERROR, stream=sys.stderr)


TOOLS_DEFINITIONS = [
    {
        "name": "jarvis_get_system_status",
        "description": "Get current Jarvis platform health, pending queue status, active schedules, and pending HITL approvals.",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "jarvis_submit_task",
        "description": "Execute a single-agent task synchronously on the Jarvis control plane.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task": {"type": "string", "description": "The task description for the agent"},
                "agent_id": {"type": "string", "description": "Optional specific agent ID (uses default if omitted)"}
            },
            "required": ["task"]
        }
    },
    {
        "name": "jarvis_list_workflows",
        "description": "List all multi-agent pipelines and Human-in-the-Loop workflows registered in Jarvis.",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "jarvis_execute_workflow",
        "description": "Trigger a multi-agent dynamic workflow (e.g. Planner -> Coder -> Reviewer).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workflow_id": {"type": "string", "description": "The ID of the workflow to execute"},
                "task": {"type": "string", "description": "The overall task specification for the workflow"}
            },
            "required": ["workflow_id", "task"]
        }
    },
    {
        "name": "jarvis_list_pending_approvals",
        "description": "List all Human-in-the-Loop approval requests currently waiting for a decision.",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "jarvis_submit_approval_decision",
        "description": "Approve or reject a paused Human-in-the-Loop workflow execution.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "execution_id": {"type": "string", "description": "The execution ID"},
                "approval_id": {"type": "string", "description": "The approval request ID"},
                "decision": {"type": "string", "enum": ["APPROVED", "REJECTED"], "description": "Decision"},
                "feedback": {"type": "string", "description": "Optional reviewer feedback"}
            },
            "required": ["execution_id", "approval_id", "decision"]
        }
    },
    {
        "name": "jarvis_list_projects",
        "description": "List all long-lived Project Workspaces, objectives, and structured context in Jarvis.",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "jarvis_query_memory",
        "description": "Query curated persistent memory rules across global, agent, or project scopes.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Keyword search query"},
                "scopes": {"type": "array", "items": {"type": "string"}, "description": "Scopes: global, agent, project"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "jarvis_propose_memory",
        "description": "Persist a new memory rule or architectural invariant into MySQL state.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "scope": {"type": "string", "enum": ["global", "agent", "project"], "description": "Memory scope"},
                "category": {"type": "string", "description": "Category e.g. preference, architecture"},
                "key": {"type": "string", "description": "Unique key name"},
                "content": {"type": "string", "description": "Memory text content"},
                "importance": {"type": "number", "description": "Importance weight (0.0 to 1.0)"},
                "target_id": {"type": "string", "description": "Agent or Project ID if scope is agent/project"}
            },
            "required": ["scope", "category", "key", "content"]
        }
    },
    {
        "name": "jarvis_submit_background_job",
        "description": "Enqueue an asynchronous background task or workflow to run on worker threads.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task": {"type": "string", "description": "Task description"},
                "agent_id": {"type": "string", "description": "Optional Agent ID"},
                "workflow_id": {"type": "string", "description": "Optional Workflow ID"},
                "priority": {"type": "integer", "description": "Priority weight (0-10)"}
            },
            "required": ["task"]
        }
    },
    {
        "name": "jarvis_query_audit_logs",
        "description": "Query security audit logs, tool permission evaluations (ALLOW, DENY, REVIEW), and events.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "decision": {"type": "string", "enum": ["ALLOW", "DENY", "REVIEW"], "description": "Filter by decision"},
                "limit": {"type": "integer", "description": "Limit count"}
            },
            "required": []
        }
    }
]

def handle_tool_call(tool_name: str, arguments: dict) -> str:
    db = SessionLocal()
    try:
        if tool_name == "jarvis_get_system_status":
            wf_svc = WorkflowService(db)
            queue_svc = QueueService(db)
            job_mgr = JobManager(db)
            pending_approvals = wf_svc.list_pending_approvals()
            queue_status = queue_svc.get_queue_status()
            jobs = job_mgr.list_jobs()
            return json.dumps({
                "status": "ONLINE",
                "pending_hitl_approvals": len(pending_approvals),
                "queue_status": queue_status,
                "total_jobs": len(jobs)
            }, indent=2)

        elif tool_name == "jarvis_submit_task":
            agent_svc = AgentService(db)
            agents = agent_svc.list_agents()
            agent_id = arguments.get("agent_id") or (agents[0].id if agents else None)
            if not agent_id:
                return "Error: No agent found in system."

            executor = SimpleAgentExecutor(db)
            exec_rec = executor.execute(task=arguments["task"], agent_id=agent_id)
            return json.dumps({
                "execution_id": exec_rec.id,
                "status": exec_rec.status,
                "output_data": exec_rec.output_data
            }, indent=2)

        elif tool_name == "jarvis_list_workflows":
            wf_svc = WorkflowService(db)
            workflows = wf_svc.list_workflows()
            return json.dumps([
                {"id": w.id, "name": w.name, "description": w.description, "status": w.status}
                for w in workflows
            ], indent=2)

        elif tool_name == "jarvis_execute_workflow":
            wf_executor = StaticWorkflowExecutor(db)
            exec_rec = wf_executor.execute(workflow_id=arguments["workflow_id"], task=arguments["task"])
            return json.dumps({
                "execution_id": exec_rec.id,
                "status": exec_rec.status,
                "output_data": exec_rec.output_data
            }, indent=2)

        elif tool_name == "jarvis_list_pending_approvals":
            wf_svc = WorkflowService(db)
            pending = wf_svc.list_pending_approvals()
            return json.dumps([
                {
                    "approval_id": a.id,
                    "execution_id": a.execution_id,
                    "node_key": a.node_key,
                    "request_type": a.request_type,
                    "created_at": str(a.created_at)
                } for a in pending
            ], indent=2)

        elif tool_name == "jarvis_submit_approval_decision":
            wf_executor = StaticWorkflowExecutor(db)
            exec_rec = wf_executor.resume_execution(
                execution_id=arguments["execution_id"],
                approval_id=arguments["approval_id"],
                decision=arguments["decision"],
                feedback=arguments.get("feedback")
            )
            return json.dumps({
                "execution_id": exec_rec.id,
                "status": exec_rec.status,
                "output_data": exec_rec.output_data
            }, indent=2)

        elif tool_name == "jarvis_list_projects":
            proj_svc = ProjectService(db)
            projects = proj_svc.list_projects()
            return json.dumps([
                {"id": p.id, "name": p.name, "objective": p.objective, "repository": p.repository}
                for p in projects
            ], indent=2)

        elif tool_name == "jarvis_query_memory":
            mem_mgr = MemoryManager(db)
            scopes = arguments.get("scopes") or ["global", "agent", "project"]
            query = arguments["query"]
            results = mem_mgr.search_vector_stubs(query=query, scopes=scopes)
            return json.dumps(results, indent=2)

        elif tool_name == "jarvis_propose_memory":
            mem_mgr = MemoryManager(db)
            cand = MemoryCandidateCreate(
                scope=arguments["scope"],
                category=arguments["category"],
                key=arguments["key"],
                content=arguments["content"],
                importance=arguments.get("importance", 1.0),
                target_id=arguments.get("target_id")
            )
            res = mem_mgr.save_memory_candidate(cand)
            return json.dumps(res, indent=2)

        elif tool_name == "jarvis_submit_background_job":
            job_mgr = JobManager(db)
            job = job_mgr.submit_job(JobCreate(
                task=arguments["task"],
                agent_id=arguments.get("agent_id"),
                workflow_id=arguments.get("workflow_id"),
                priority=arguments.get("priority", 0)
            ))
            return json.dumps({"job_id": job.id, "status": job.status, "queue_message_id": job.queue_message_id}, indent=2)

        elif tool_name == "jarvis_query_audit_logs":
            decision = arguments.get("decision")
            limit = arguments.get("limit", 10)
            q = db.query(AuditEvent)
            if decision:
                q = q.filter(AuditEvent.decision == decision)
            events = q.order_by(AuditEvent.timestamp.desc()).limit(limit).all()
            return json.dumps([
                {
                    "id": e.id,
                    "action": e.action,
                    "tool_name": e.tool_name,
                    "decision": e.decision,
                    "timestamp": str(e.timestamp)
                } for e in events
            ], indent=2)

        else:
            return f"Error: Unknown tool '{tool_name}'."
    except Exception as e:
        return f"Error executing tool '{tool_name}': {str(e)}"
    finally:
        db.close()


def send_response(response: dict):
    body = json.dumps(response)
    sys.stdout.write(body + "\n")
    sys.stdout.flush()

def main():
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        line = line.strip()
        if not line:
            continue

        try:
            req = json.loads(line)
        except Exception:
            continue

        msg_id = req.get("id")
        method = req.get("method")
        params = req.get("params", {})

        if method == "initialize":
            send_response({
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "jarvis-mcp-server", "version": "1.0.0"}
                }
            })
        elif method == "notifications/initialized":
            pass
        elif method == "tools/list":
            send_response({
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {"tools": TOOLS_DEFINITIONS}
            })
        elif method == "tools/call":
            name = params.get("name")
            args = params.get("arguments", {})
            result_text = handle_tool_call(name, args)
            send_response({
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "content": [{"type": "text", "text": result_text}]
                }
            })
        else:
            if msg_id is not None:
                send_response({
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {"code": -32601, "message": f"Method '{method}' not found."}
                })

if __name__ == "__main__":
    main()
