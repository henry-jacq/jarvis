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

# Services
from app.services.agent_service import AgentService
from app.services.workflow_service import WorkflowService
from app.services.project_service import ProjectService
from app.services.job_manager import JobManager
from app.services.queue_service import QueueService
from app.services.memory_manager import MemoryManager
from app.services.conversation_service import ConversationService
from app.services.scheduler_service import SchedulerService
from app.services.settings_service import SettingsService

# Runtimes
from app.runtime.executor import SimpleAgentExecutor
from app.runtime.workflow_executor import StaticWorkflowExecutor

# Schemas
from app.schemas.job import JobCreate
from app.schemas.memory import MemoryCandidateCreate
from app.schemas.agent import AgentCreate, AgentVersionCreate
from app.schemas.project import ProjectCreate
from app.schemas.workflow import WorkflowCreate, WorkflowVersionCreate, WorkflowNodeCreate, WorkflowEdgeCreate, WorkflowAgentBindingCreate
from app.schemas.conversation import ConversationCreate, MessageCreate
from app.schemas.schedule import ScheduleCreate
from app.schemas.setting import AppSettingCreate

# Models (for direct queries)
from app.models.security import AuditEvent
from app.models.executions import Execution, ExecutionEvent

logging.basicConfig(level=logging.ERROR, stream=sys.stderr)


# ---------------------------------------------------------------------------
# Tool definitions — 32 tools across 9 capability groups
# ---------------------------------------------------------------------------

TOOLS_DEFINITIONS = [

    # ── PLATFORM STATUS ──────────────────────────────────────────────────────
    {
        "name": "jarvis_get_system_status",
        "description": (
            "Get a full Jarvis platform health snapshot: online status, "
            "agent/workflow/project/schedule/job counts, pending HITL approvals, "
            "and queue depth."
        ),
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    },

    # ── AGENT MANAGEMENT ─────────────────────────────────────────────────────
    {
        "name": "jarvis_list_agents",
        "description": "List all registered agents with id, name, role, status, and active_version_id.",
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "jarvis_get_agent",
        "description": "Get full details for a single agent including its active version config (system prompt, model, temperature, policies).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "agent_id": {"type": "string", "description": "Agent ID"}
            },
            "required": ["agent_id"]
        }
    },
    {
        "name": "jarvis_create_agent",
        "description": (
            "Create a new agent with an initial version. "
            "Specify name, role, system_prompt, model_provider, model_name and optional policies."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "name":          {"type": "string",  "description": "Unique agent name"},
                "role":          {"type": "string",  "description": "Agent role label (e.g. 'Planner', 'Coder')"},
                "purpose":       {"type": "string",  "description": "Short description of the agent's purpose"},
                "system_prompt": {"type": "string",  "description": "System-level instruction for the agent"},
                "model_provider":{"type": "string",  "description": "LLM provider: 'ollama', 'openai', 'anthropic'", "default": "ollama"},
                "model_name":    {"type": "string",  "description": "Model name e.g. 'llama3.2', 'gpt-4o'",          "default": "llama3.2"},
                "temperature":   {"type": "number",  "description": "Sampling temperature (0.0–1.0)",               "default": 0.7},
                "tool_policy":   {"type": "object",  "description": "Tool permission policy {allowed:[], denied:[], requires_approval:[]}"},
                "memory_policy": {"type": "object",  "description": "Memory scope policy {read_scopes:[global,agent,project], write:true}"},
                "context_policy":{"type": "object",  "description": "Context budget policy {max_tokens:4096}"}
            },
            "required": ["name", "role", "system_prompt"]
        }
    },
    {
        "name": "jarvis_publish_agent_version",
        "description": "Publish a new version of an existing agent (update prompt, model, temperature, or policies). The new version becomes the active one immediately.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "agent_id":      {"type": "string", "description": "Target agent ID"},
                "system_prompt": {"type": "string", "description": "New system prompt"},
                "model_provider":{"type": "string", "description": "LLM provider"},
                "model_name":    {"type": "string", "description": "Model name"},
                "temperature":   {"type": "number", "description": "Temperature"},
                "tool_policy":   {"type": "object", "description": "Tool policy override"},
                "memory_policy": {"type": "object", "description": "Memory policy override"},
                "context_policy":{"type": "object", "description": "Context policy override"}
            },
            "required": ["agent_id", "system_prompt"]
        }
    },

    # ── TASK EXECUTION ────────────────────────────────────────────────────────
    {
        "name": "jarvis_submit_task",
        "description": "Execute a single-agent task synchronously on the Jarvis control plane. Returns the full execution output.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task":       {"type": "string", "description": "The task description for the agent"},
                "agent_id":   {"type": "string", "description": "Optional specific agent ID (uses first agent if omitted)"},
                "project_id": {"type": "string", "description": "Optional project ID for context injection"}
            },
            "required": ["task"]
        }
    },

    # ── EXECUTION INSPECTION ─────────────────────────────────────────────────
    {
        "name": "jarvis_get_execution",
        "description": "Inspect any execution record by ID — status, output, token usage, timing, and error message.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "execution_id": {"type": "string", "description": "Execution ID to look up"}
            },
            "required": ["execution_id"]
        }
    },
    {
        "name": "jarvis_list_executions",
        "description": "List recent executions. Filter by status (RUNNING, COMPLETED, FAILED, WAITING_FOR_APPROVAL) and/or type (SIMPLE, STATIC_WORKFLOW).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "description": "Filter by status e.g. COMPLETED, FAILED, RUNNING"},
                "type":   {"type": "string", "description": "Filter by type: SIMPLE or STATIC_WORKFLOW"},
                "limit":  {"type": "integer","description": "Max records to return (default 20)"}
            },
            "required": []
        }
    },
    {
        "name": "jarvis_get_execution_events",
        "description": "Get the full ordered event trace for an execution — agent_start, llm_call, tool_request, memory_persisted, workflow_node_completed, etc. Great for debugging.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "execution_id": {"type": "string", "description": "Execution ID"}
            },
            "required": ["execution_id"]
        }
    },

    # ── WORKFLOW MANAGEMENT ───────────────────────────────────────────────────
    {
        "name": "jarvis_list_workflows",
        "description": "List all multi-agent pipelines and Human-in-the-Loop workflows registered in Jarvis.",
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "jarvis_get_workflow",
        "description": "Get full workflow details including nodes, edges, agent bindings, and version info.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workflow_id": {"type": "string", "description": "Workflow ID"}
            },
            "required": ["workflow_id"]
        }
    },
    {
        "name": "jarvis_create_workflow",
        "description": (
            "Create a new named multi-agent workflow. Define nodes (agent/human_approval/tool), "
            "directed edges, and agent bindings. Node types: 'agent', 'human_approval', 'tool'. "
            "Edges can have condition_expression (Python bool expr, e.g. \"results.get('plan') != ''\"). "
            "The first node in the nodes array is the entry point."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "name":        {"type": "string", "description": "Workflow name"},
                "description": {"type": "string", "description": "Workflow description"},
                "nodes": {
                    "type": "array",
                    "description": "Ordered list of workflow nodes",
                    "items": {
                        "type": "object",
                        "properties": {
                            "node_key":       {"type": "string"},
                            "node_type":      {"type": "string", "enum": ["agent", "human_approval", "tool"]},
                            "agent_id":       {"type": "string"},
                            "prompt_overlay": {"type": "string"}
                        },
                        "required": ["node_key", "node_type"]
                    }
                },
                "edges": {
                    "type": "array",
                    "description": "Directed edges between nodes",
                    "items": {
                        "type": "object",
                        "properties": {
                            "source_node_key":      {"type": "string"},
                            "target_node_key":      {"type": "string"},
                            "condition_expression": {"type": "string"}
                        },
                        "required": ["source_node_key", "target_node_key"]
                    }
                },
                "agent_bindings": {
                    "type": "array",
                    "description": "Agent role bindings for the workflow",
                    "items": {
                        "type": "object",
                        "properties": {
                            "agent_id":       {"type": "string"},
                            "role":           {"type": "string"},
                            "prompt_overlay": {"type": "string"}
                        },
                        "required": ["agent_id", "role"]
                    }
                }
            },
            "required": ["name", "nodes", "edges", "agent_bindings"]
        }
    },
    {
        "name": "jarvis_execute_workflow",
        "description": "Trigger a multi-agent dynamic workflow (e.g. Planner → Coder → Reviewer). Supports optional project context injection.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workflow_id": {"type": "string", "description": "The ID of the workflow to execute"},
                "task":        {"type": "string", "description": "The overall task specification"},
                "project_id":  {"type": "string", "description": "Optional project ID for context injection"}
            },
            "required": ["workflow_id", "task"]
        }
    },

    # ── HITL APPROVALS ────────────────────────────────────────────────────────
    {
        "name": "jarvis_list_pending_approvals",
        "description": "List all Human-in-the-Loop approval requests currently waiting for a decision.",
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "jarvis_submit_approval_decision",
        "description": "Approve or reject a paused Human-in-the-Loop workflow execution.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "execution_id": {"type": "string", "description": "The execution ID"},
                "approval_id":  {"type": "string", "description": "The approval request ID"},
                "decision":     {"type": "string", "enum": ["APPROVED", "REJECTED"], "description": "Decision"},
                "feedback":     {"type": "string", "description": "Optional reviewer feedback"}
            },
            "required": ["execution_id", "approval_id", "decision"]
        }
    },

    # ── PROJECT MANAGEMENT ────────────────────────────────────────────────────
    {
        "name": "jarvis_list_projects",
        "description": "List all long-lived Project Workspaces with id, name, objective, repository, status, and task/document counts.",
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "jarvis_create_project",
        "description": "Create a new Project Workspace with an objective, description, optional repository URL, and initial structured context.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name":               {"type": "string", "description": "Project name"},
                "objective":          {"type": "string", "description": "High-level project objective"},
                "description":        {"type": "string", "description": "Detailed description"},
                "repository":         {"type": "string", "description": "Optional repository URL"},
                "structured_context": {"type": "object","description": "Key-value context pairs injected into agent prompts"}
            },
            "required": ["name"]
        }
    },
    {
        "name": "jarvis_get_project",
        "description": "Get full project details including all tasks, documents, and structured context.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string", "description": "Project ID"}
            },
            "required": ["project_id"]
        }
    },
    {
        "name": "jarvis_add_project_task",
        "description": "Append a task item to a project's task list.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string", "description": "Project ID"},
                "title":      {"type": "string", "description": "Task title"},
                "description":{"type": "string", "description": "Task description"},
                "status":     {"type": "string", "description": "Task status: pending, in_progress, done", "default": "pending"},
                "priority":   {"type": "string", "description": "Priority: low, medium, high",           "default": "medium"}
            },
            "required": ["project_id", "title"]
        }
    },

    # ── CONVERSATION MANAGEMENT ───────────────────────────────────────────────
    {
        "name": "jarvis_list_conversations",
        "description": "List conversations. Optionally filter by project_id.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string", "description": "Optional project ID to filter by"},
                "limit":      {"type": "integer","description": "Max conversations to return (default 20)"}
            },
            "required": []
        }
    },
    {
        "name": "jarvis_create_conversation",
        "description": "Create a new conversation thread, optionally linked to a project.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "title":           {"type": "string", "description": "Conversation title"},
                "project_id":      {"type": "string", "description": "Optional project to attach to"},
                "initial_message": {"type": "string", "description": "Optional first user message content"}
            },
            "required": []
        }
    },
    {
        "name": "jarvis_get_conversation_messages",
        "description": "Fetch message history for a conversation.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "conversation_id": {"type": "string", "description": "Conversation ID"},
                "limit":           {"type": "integer","description": "Max messages to return (default 50)"}
            },
            "required": ["conversation_id"]
        }
    },

    # ── SCHEDULER ─────────────────────────────────────────────────────────────
    {
        "name": "jarvis_list_schedules",
        "description": "List all recurring agent schedules with name, expression, next_run_at, last_run_at, enabled status.",
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "jarvis_create_schedule",
        "description": (
            "Create a recurring schedule that enqueues an agent task automatically. "
            "schedule_expression formats: 'interval:3600' (every N seconds) or 'cron:0 9 * * *'. "
            "task_input must include a 'task' key."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "name":                {"type": "string", "description": "Schedule name"},
                "agent_id":            {"type": "string", "description": "Agent ID to run"},
                "schedule_expression": {"type": "string", "description": "e.g. 'interval:3600' or 'cron:0 9 * * *'"},
                "task_input":          {"type": "object", "description": "Must include {'task': '...'} and optional override_config"},
                "project_id":          {"type": "string", "description": "Optional project ID"},
                "enabled":             {"type": "boolean","description": "Enable immediately (default true)"}
            },
            "required": ["name", "agent_id", "schedule_expression", "task_input"]
        }
    },
    {
        "name": "jarvis_evaluate_schedules",
        "description": "Manually trigger schedule evaluation — fires any overdue schedules and enqueues their jobs. Returns list of triggered schedule-job pairs.",
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "jarvis_get_schedule",
        "description": "Get a single schedule by ID with full configuration.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "schedule_id": {"type": "string", "description": "Schedule ID"}
            },
            "required": ["schedule_id"]
        }
    },

    # ── MEMORY ────────────────────────────────────────────────────────────────
    {
        "name": "jarvis_query_memory",
        "description": "Query curated persistent memory rules across global, agent, or project scopes using keyword search.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query":  {"type": "string", "description": "Keyword search query"},
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
                "scope":      {"type": "string", "enum": ["global", "agent", "project"], "description": "Memory scope"},
                "category":   {"type": "string", "description": "Category e.g. preference, architecture"},
                "key":        {"type": "string", "description": "Unique key name"},
                "content":    {"type": "string", "description": "Memory text content"},
                "importance": {"type": "number", "description": "Importance weight 0.0–1.0"},
                "target_id":  {"type": "string", "description": "Agent or Project ID if scope is agent/project"}
            },
            "required": ["scope", "category", "key", "content"]
        }
    },
    {
        "name": "jarvis_get_full_memory",
        "description": "Dump all memory items for a given scope. For agent/project scope supply the corresponding target_id.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "scope":     {"type": "string", "enum": ["global", "agent", "project"], "description": "Memory scope"},
                "target_id": {"type": "string", "description": "Agent ID or Project ID (required for agent/project scope)"},
                "min_importance": {"type": "number", "description": "Minimum importance threshold (default 0.0)"}
            },
            "required": ["scope"]
        }
    },
    {
        "name": "jarvis_apply_memory_decay",
        "description": "Apply an importance decay factor to all memory records (soft eviction). Returns count of records updated.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "decay_factor": {"type": "number", "description": "Multiplicative decay factor 0.0–1.0 (default 0.9)"}
            },
            "required": []
        }
    },

    # ── JOBS & QUEUE ──────────────────────────────────────────────────────────
    {
        "name": "jarvis_submit_background_job",
        "description": "Enqueue an asynchronous background task or workflow to run on worker threads.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task":        {"type": "string",  "description": "Task description"},
                "agent_id":    {"type": "string",  "description": "Optional Agent ID"},
                "workflow_id": {"type": "string",  "description": "Optional Workflow ID"},
                "project_id":  {"type": "string",  "description": "Optional Project ID"},
                "priority":    {"type": "integer", "description": "Priority weight 0–10 (default 0)"}
            },
            "required": ["task"]
        }
    },
    {
        "name": "jarvis_list_jobs",
        "description": "List recent background jobs. Optionally filter by status (PENDING, QUEUED, COMPLETED, FAILED, CANCELLED).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "status": {"type": "string",  "description": "Filter by job status"},
                "limit":  {"type": "integer", "description": "Max records (default 20)"}
            },
            "required": []
        }
    },
    {
        "name": "jarvis_get_job",
        "description": "Get a single job by ID including its attempt history (latency, errors, retries).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "job_id": {"type": "string", "description": "Job ID"}
            },
            "required": ["job_id"]
        }
    },
    {
        "name": "jarvis_cancel_job",
        "description": "Cancel a queued or running background job. Marks it CANCELLED and dead-letters its queue message.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "job_id": {"type": "string", "description": "Job ID to cancel"}
            },
            "required": ["job_id"]
        }
    },

    # ── SETTINGS ──────────────────────────────────────────────────────────────
    {
        "name": "jarvis_list_settings",
        "description": "List all platform application settings. Optionally filter by category.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "category": {"type": "string", "description": "Optional category filter e.g. 'general', 'llm', 'security'"}
            },
            "required": []
        }
    },
    {
        "name": "jarvis_set_setting",
        "description": "Create or update a platform application setting.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "key":         {"type": "string", "description": "Setting key"},
                "value":       {"type": "string", "description": "Setting value (always string)"},
                "category":    {"type": "string", "description": "Category e.g. 'general', 'llm'", "default": "general"},
                "data_type":   {"type": "string", "description": "Data type: string, integer, float, boolean", "default": "string"},
                "description": {"type": "string", "description": "Human-readable description"}
            },
            "required": ["key", "value"]
        }
    },

    # ── SECURITY & AUDIT ──────────────────────────────────────────────────────
    {
        "name": "jarvis_query_audit_logs",
        "description": "Query security audit logs — tool permission evaluations (ALLOW, DENY, REVIEW), actor, agent, and tool filters.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "decision":  {"type": "string", "enum": ["ALLOW", "DENY", "REVIEW"], "description": "Filter by decision"},
                "agent_id":  {"type": "string", "description": "Filter by agent ID"},
                "tool_name": {"type": "string", "description": "Filter by tool name"},
                "limit":     {"type": "integer","description": "Max records (default 20)"}
            },
            "required": []
        }
    },
]


# ---------------------------------------------------------------------------
# Tool handler — dispatches every tool call to the appropriate service
# ---------------------------------------------------------------------------

def handle_tool_call(tool_name: str, arguments: dict) -> str:
    db = SessionLocal()
    try:

        # ── PLATFORM STATUS ─────────────────────────────────────────────────
        if tool_name == "jarvis_get_system_status":
            agent_svc   = AgentService(db)
            wf_svc      = WorkflowService(db)
            proj_svc    = ProjectService(db)
            queue_svc   = QueueService(db)
            job_mgr     = JobManager(db)
            sched_svc   = SchedulerService(db)

            pending_approvals = wf_svc.list_pending_approvals()
            queue_status      = queue_svc.get_queue_status()
            jobs              = job_mgr.list_jobs()
            schedules         = sched_svc.list_schedules()

            return json.dumps({
                "status":               "ONLINE",
                "agents":               len(agent_svc.list_agents()),
                "workflows":            len(wf_svc.list_workflows()),
                "projects":             len(proj_svc.list_projects()),
                "active_schedules":     sum(1 for s in schedules if s.enabled),
                "total_jobs":           len(jobs),
                "pending_jobs":         sum(1 for j in jobs if j.status in ("PENDING", "QUEUED")),
                "pending_hitl_approvals": len(pending_approvals),
                "queue_status":         queue_status,
            }, indent=2, default=str)

        # ── AGENT MANAGEMENT ────────────────────────────────────────────────
        elif tool_name == "jarvis_list_agents":
            agent_svc = AgentService(db)
            agents = agent_svc.list_agents()
            return json.dumps([
                {
                    "id":                a.id,
                    "name":              a.name,
                    "role":              a.role,
                    "purpose":           a.purpose,
                    "status":            a.status,
                    "active_version_id": a.active_version_id,
                    "created_at":        str(a.created_at),
                }
                for a in agents
            ], indent=2)

        elif tool_name == "jarvis_get_agent":
            agent_svc = AgentService(db)
            agent = agent_svc.get_agent(arguments["agent_id"])
            if not agent:
                return f"Error: Agent '{arguments['agent_id']}' not found."
            ver = agent_svc.get_active_version(agent)
            result = {
                "id":      agent.id,
                "name":    agent.name,
                "role":    agent.role,
                "purpose": agent.purpose,
                "status":  agent.status,
                "active_version": {
                    "id":             ver.id,
                    "version":        ver.version,
                    "model_provider": ver.model_provider,
                    "model_name":     ver.model_name,
                    "temperature":    ver.temperature,
                    "system_prompt":  ver.system_prompt,
                    "tool_policy":    ver.tool_policy,
                    "memory_policy":  ver.memory_policy,
                    "context_policy": ver.context_policy,
                } if ver else None
            }
            return json.dumps(result, indent=2, default=str)

        elif tool_name == "jarvis_create_agent":
            agent_svc = AgentService(db)
            ver_payload = AgentVersionCreate(
                system_prompt  = arguments["system_prompt"],
                model_provider = arguments.get("model_provider", "ollama"),
                model_name     = arguments.get("model_name", "llama3.2"),
                temperature    = arguments.get("temperature", 0.7),
                tool_policy    = arguments.get("tool_policy", {"allowed": [], "denied": []}),
                memory_policy  = arguments.get("memory_policy", {"read_scopes": ["global", "agent", "project"], "write": True}),
                context_policy = arguments.get("context_policy", {"max_tokens": 4096}),
            )
            agent = agent_svc.create_agent(AgentCreate(
                name    = arguments["name"],
                role    = arguments["role"],
                purpose = arguments.get("purpose"),
                initial_version = ver_payload
            ))
            return json.dumps({
                "id":                agent.id,
                "name":              agent.name,
                "role":              agent.role,
                "active_version_id": agent.active_version_id,
                "status":            agent.status,
            }, indent=2)

        elif tool_name == "jarvis_publish_agent_version":
            agent_svc = AgentService(db)
            agent = agent_svc.get_agent(arguments["agent_id"])
            if not agent:
                return f"Error: Agent '{arguments['agent_id']}' not found."
            # Use current version as defaults if not specified
            current = agent_svc.get_active_version(agent)
            ver = agent_svc.publish_new_version(
                agent_id = arguments["agent_id"],
                ver_payload = AgentVersionCreate(
                    system_prompt  = arguments["system_prompt"],
                    model_provider = arguments.get("model_provider", current.model_provider if current else "ollama"),
                    model_name     = arguments.get("model_name",     current.model_name     if current else "llama3.2"),
                    temperature    = arguments.get("temperature",    current.temperature    if current else 0.7),
                    tool_policy    = arguments.get("tool_policy",    current.tool_policy    if current else {}),
                    memory_policy  = arguments.get("memory_policy",  current.memory_policy  if current else {}),
                    context_policy = arguments.get("context_policy", current.context_policy if current else {}),
                )
            )
            return json.dumps({
                "agent_id":   arguments["agent_id"],
                "version_id": ver.id,
                "version":    ver.version,
                "model":      f"{ver.model_provider}/{ver.model_name}",
            }, indent=2)

        # ── TASK EXECUTION ───────────────────────────────────────────────────
        elif tool_name == "jarvis_submit_task":
            agent_svc = AgentService(db)
            agents = agent_svc.list_agents()
            agent_id = arguments.get("agent_id") or (agents[0].id if agents else None)
            if not agent_id:
                return "Error: No agent found in system. Create one with jarvis_create_agent first."

            executor = SimpleAgentExecutor(db)
            exec_rec = executor.execute(
                task       = arguments["task"],
                agent_id   = agent_id,
                project_id = arguments.get("project_id"),
            )
            return json.dumps({
                "execution_id":    exec_rec.id,
                "status":          exec_rec.status,
                "output_data":     exec_rec.output_data,
                "total_tokens":    exec_rec.total_tokens,
                "execution_ms":    exec_rec.execution_time_ms,
                "error_message":   exec_rec.error_message,
            }, indent=2, default=str)

        # ── EXECUTION INSPECTION ─────────────────────────────────────────────
        elif tool_name == "jarvis_get_execution":
            exec_rec = db.query(Execution).filter(Execution.id == arguments["execution_id"]).first()
            if not exec_rec:
                return f"Error: Execution '{arguments['execution_id']}' not found."
            return json.dumps({
                "id":              exec_rec.id,
                "type":            exec_rec.type,
                "status":          exec_rec.status,
                "agent_id":        exec_rec.agent_id,
                "project_id":      exec_rec.project_id,
                "input_data":      exec_rec.input_data,
                "output_data":     exec_rec.output_data,
                "error_message":   exec_rec.error_message,
                "input_tokens":    exec_rec.input_tokens,
                "output_tokens":   exec_rec.output_tokens,
                "total_tokens":    exec_rec.total_tokens,
                "execution_ms":    exec_rec.execution_time_ms,
                "started_at":      str(exec_rec.started_at),
                "completed_at":    str(exec_rec.completed_at),
            }, indent=2, default=str)

        elif tool_name == "jarvis_list_executions":
            limit  = arguments.get("limit", 20)
            q = db.query(Execution)
            if arguments.get("status"):
                q = q.filter(Execution.status == arguments["status"])
            if arguments.get("type"):
                q = q.filter(Execution.type == arguments["type"])
            execs = q.order_by(Execution.created_at.desc()).limit(limit).all()
            return json.dumps([
                {
                    "id":           e.id,
                    "type":         e.type,
                    "status":       e.status,
                    "agent_id":     e.agent_id,
                    "project_id":   e.project_id,
                    "total_tokens": e.total_tokens,
                    "execution_ms": e.execution_time_ms,
                    "created_at":   str(e.created_at),
                }
                for e in execs
            ], indent=2)

        elif tool_name == "jarvis_get_execution_events":
            events = db.query(ExecutionEvent).filter(
                ExecutionEvent.execution_id == arguments["execution_id"]
            ).order_by(ExecutionEvent.timestamp.asc()).all()
            return json.dumps([
                {
                    "event_type": e.event_type,
                    "payload":    e.payload,
                    "timestamp":  str(e.timestamp),
                }
                for e in events
            ], indent=2, default=str)

        # ── WORKFLOW MANAGEMENT ──────────────────────────────────────────────
        elif tool_name == "jarvis_list_workflows":
            wf_svc = WorkflowService(db)
            workflows = wf_svc.list_workflows()
            return json.dumps([
                {
                    "id":                w.id,
                    "name":              w.name,
                    "description":       w.description,
                    "status":            w.status,
                    "active_version_id": w.active_version_id,
                }
                for w in workflows
            ], indent=2)

        elif tool_name == "jarvis_get_workflow":
            wf_svc = WorkflowService(db)
            wf = wf_svc.get_workflow(arguments["workflow_id"])
            if not wf:
                return f"Error: Workflow '{arguments['workflow_id']}' not found."
            ver = wf_svc.get_active_version(wf.id)
            details = wf_svc.get_version_details(ver.id) if ver else {}
            return json.dumps({
                "id":          wf.id,
                "name":        wf.name,
                "description": wf.description,
                "status":      wf.status,
                "version":     ver.version if ver else None,
                "nodes": [
                    {"node_key": n.node_key, "node_type": n.node_type, "agent_id": n.agent_id}
                    for n in details.get("nodes", [])
                ],
                "edges": [
                    {"source": e.source_node_key, "target": e.target_node_key, "condition": e.condition_expression}
                    for e in details.get("edges", [])
                ],
                "agent_bindings": [
                    {"agent_id": b.agent_id, "role": b.role}
                    for b in details.get("bindings", [])
                ],
            }, indent=2, default=str)

        elif tool_name == "jarvis_create_workflow":
            wf_svc = WorkflowService(db)

            nodes = [
                WorkflowNodeCreate(
                    node_key       = n["node_key"],
                    node_type      = n.get("node_type", "agent"),
                    agent_id       = n.get("agent_id"),
                    prompt_overlay = n.get("prompt_overlay"),
                )
                for n in arguments.get("nodes", [])
            ]
            edges = [
                WorkflowEdgeCreate(
                    source_node_key      = e["source_node_key"],
                    target_node_key      = e["target_node_key"],
                    condition_expression = e.get("condition_expression"),
                )
                for e in arguments.get("edges", [])
            ]
            bindings = [
                WorkflowAgentBindingCreate(
                    agent_id       = b["agent_id"],
                    role           = b["role"],
                    prompt_overlay = b.get("prompt_overlay"),
                )
                for b in arguments.get("agent_bindings", [])
            ]

            wf = wf_svc.create_workflow(WorkflowCreate(
                name        = arguments["name"],
                description = arguments.get("description"),
                initial_version = WorkflowVersionCreate(
                    nodes          = nodes,
                    edges          = edges,
                    agent_bindings = bindings,
                )
            ))
            return json.dumps({
                "id":                wf.id,
                "name":              wf.name,
                "status":            wf.status,
                "active_version_id": wf.active_version_id,
            }, indent=2)

        elif tool_name == "jarvis_execute_workflow":
            wf_executor = StaticWorkflowExecutor(db)
            exec_rec = wf_executor.execute(
                workflow_id = arguments["workflow_id"],
                task        = arguments["task"],
                project_id  = arguments.get("project_id"),
            )
            return json.dumps({
                "execution_id": exec_rec.id,
                "status":       exec_rec.status,
                "output_data":  exec_rec.output_data,
                "total_tokens": exec_rec.total_tokens,
                "execution_ms": exec_rec.execution_time_ms,
            }, indent=2, default=str)

        # ── HITL APPROVALS ───────────────────────────────────────────────────
        elif tool_name == "jarvis_list_pending_approvals":
            wf_svc = WorkflowService(db)
            pending = wf_svc.list_pending_approvals()
            return json.dumps([
                {
                    "approval_id":    a.id,
                    "execution_id":   a.execution_id,
                    "node_key":       a.node_key,
                    "request_type":   a.request_type,
                    "tool_name":      a.tool_name,
                    "tool_args":      a.tool_args,
                    "created_at":     str(a.created_at),
                }
                for a in pending
            ], indent=2)

        elif tool_name == "jarvis_submit_approval_decision":
            wf_executor = StaticWorkflowExecutor(db)
            exec_rec = wf_executor.resume_execution(
                execution_id = arguments["execution_id"],
                approval_id  = arguments["approval_id"],
                decision     = arguments["decision"],
                feedback     = arguments.get("feedback"),
            )
            return json.dumps({
                "execution_id": exec_rec.id,
                "status":       exec_rec.status,
                "output_data":  exec_rec.output_data,
            }, indent=2, default=str)

        # ── PROJECT MANAGEMENT ───────────────────────────────────────────────
        elif tool_name == "jarvis_list_projects":
            proj_svc = ProjectService(db)
            projects = proj_svc.list_projects()
            return json.dumps([
                {
                    "id":          p.id,
                    "name":        p.name,
                    "objective":   p.objective,
                    "repository":  p.repository,
                    "status":      p.status,
                    "task_count":  len(p.project_tasks or []),
                    "doc_count":   len(p.project_documents or []),
                }
                for p in projects
            ], indent=2)

        elif tool_name == "jarvis_create_project":
            proj_svc = ProjectService(db)
            project = proj_svc.create_project(ProjectCreate(
                name               = arguments["name"],
                objective          = arguments.get("objective"),
                description        = arguments.get("description"),
                repository         = arguments.get("repository"),
                structured_context = arguments.get("structured_context", {}),
            ))
            return json.dumps({
                "id":        project.id,
                "name":      project.name,
                "objective": project.objective,
                "status":    project.status,
            }, indent=2)

        elif tool_name == "jarvis_get_project":
            proj_svc = ProjectService(db)
            project = proj_svc.get_project(arguments["project_id"])
            if not project:
                return f"Error: Project '{arguments['project_id']}' not found."
            convs = proj_svc.list_attached_conversations(project.id)
            return json.dumps({
                "id":                 project.id,
                "name":               project.name,
                "objective":          project.objective,
                "description":        project.description,
                "repository":         project.repository,
                "status":             project.status,
                "structured_context": project.structured_context,
                "project_tasks":      project.project_tasks,
                "project_documents":  project.project_documents,
                "conversation_count": len(convs),
            }, indent=2, default=str)

        elif tool_name == "jarvis_add_project_task":
            proj_svc = ProjectService(db)
            task_item = {
                "title":       arguments["title"],
                "description": arguments.get("description", ""),
                "status":      arguments.get("status", "pending"),
                "priority":    arguments.get("priority", "medium"),
            }
            project = proj_svc.add_project_task(arguments["project_id"], task_item)
            return json.dumps({
                "project_id": project.id,
                "task_count": len(project.project_tasks or []),
                "added_task": task_item,
            }, indent=2)

        # ── CONVERSATION MANAGEMENT ──────────────────────────────────────────
        elif tool_name == "jarvis_list_conversations":
            from app.models.conversations import Conversation
            limit = arguments.get("limit", 20)
            q = db.query(Conversation)
            if arguments.get("project_id"):
                q = q.filter(Conversation.project_id == arguments["project_id"])
            convs = q.order_by(Conversation.created_at.desc()).limit(limit).all()
            return json.dumps([
                {
                    "id":         c.id,
                    "title":      c.title,
                    "project_id": c.project_id,
                    "status":     c.status,
                    "created_at": str(c.created_at),
                }
                for c in convs
            ], indent=2)

        elif tool_name == "jarvis_create_conversation":
            conv_svc = ConversationService(db)
            initial_msg = None
            if arguments.get("initial_message"):
                initial_msg = MessageCreate(role="user", content=arguments["initial_message"])
            conv = conv_svc.create_conversation(ConversationCreate(
                title           = arguments.get("title", "New Conversation"),
                project_id      = arguments.get("project_id"),
                initial_message = initial_msg,
            ))
            return json.dumps({
                "id":         conv.id,
                "title":      conv.title,
                "project_id": conv.project_id,
                "status":     conv.status,
            }, indent=2)

        elif tool_name == "jarvis_get_conversation_messages":
            conv_svc = ConversationService(db)
            limit = arguments.get("limit", 50)
            messages = conv_svc.get_messages(arguments["conversation_id"], limit=limit)
            return json.dumps([
                {
                    "id":         m.id,
                    "role":       m.role,
                    "content":    m.content,
                    "created_at": str(m.created_at),
                }
                for m in messages
            ], indent=2)

        # ── SCHEDULER ────────────────────────────────────────────────────────
        elif tool_name == "jarvis_list_schedules":
            sched_svc = SchedulerService(db)
            schedules = sched_svc.list_schedules()
            return json.dumps([
                {
                    "id":                  s.id,
                    "name":                s.name,
                    "agent_id":            s.agent_id,
                    "project_id":          s.project_id,
                    "schedule_expression": s.schedule_expression,
                    "enabled":             s.enabled,
                    "next_run_at":         str(s.next_run_at),
                    "last_run_at":         str(s.last_run_at),
                    "task_input":          s.task_input,
                }
                for s in schedules
            ], indent=2, default=str)

        elif tool_name == "jarvis_create_schedule":
            sched_svc = SchedulerService(db)
            sched = sched_svc.create_schedule(ScheduleCreate(
                name                = arguments["name"],
                agent_id            = arguments["agent_id"],
                project_id          = arguments.get("project_id"),
                schedule_expression = arguments["schedule_expression"],
                task_input          = arguments["task_input"],
                enabled             = arguments.get("enabled", True),
            ))
            return json.dumps({
                "id":                  sched.id,
                "name":                sched.name,
                "schedule_expression": sched.schedule_expression,
                "next_run_at":         str(sched.next_run_at),
                "enabled":             sched.enabled,
            }, indent=2, default=str)

        elif tool_name == "jarvis_evaluate_schedules":
            sched_svc = SchedulerService(db)
            triggered = sched_svc.evaluate_schedules()
            return json.dumps({
                "triggered_count": len(triggered),
                "triggered":       triggered,
            }, indent=2)

        elif tool_name == "jarvis_get_schedule":
            sched_svc = SchedulerService(db)
            sched = sched_svc.get_schedule(arguments["schedule_id"])
            if not sched:
                return f"Error: Schedule '{arguments['schedule_id']}' not found."
            return json.dumps({
                "id":                  sched.id,
                "name":                sched.name,
                "agent_id":            sched.agent_id,
                "project_id":          sched.project_id,
                "schedule_expression": sched.schedule_expression,
                "timezone":            sched.timezone,
                "enabled":             sched.enabled,
                "next_run_at":         str(sched.next_run_at),
                "last_run_at":         str(sched.last_run_at),
                "task_input":          sched.task_input,
            }, indent=2, default=str)

        # ── MEMORY ───────────────────────────────────────────────────────────
        elif tool_name == "jarvis_query_memory":
            mem_mgr = MemoryManager(db)
            scopes  = arguments.get("scopes") or ["global", "agent", "project"]
            results = mem_mgr.search_vector_stubs(query=arguments["query"], scopes=scopes)
            return json.dumps(results, indent=2, default=str)

        elif tool_name == "jarvis_propose_memory":
            mem_mgr = MemoryManager(db)
            cand = MemoryCandidateCreate(
                scope      = arguments["scope"],
                category   = arguments["category"],
                key        = arguments["key"],
                content    = arguments["content"],
                importance = arguments.get("importance", 1.0),
                target_id  = arguments.get("target_id"),
            )
            res = mem_mgr.save_memory_candidate(cand)
            return json.dumps(res, indent=2, default=str)

        elif tool_name == "jarvis_get_full_memory":
            mem_mgr      = MemoryManager(db)
            scope        = arguments["scope"]
            target_id    = arguments.get("target_id")
            min_imp      = arguments.get("min_importance", 0.0)
            agent_id     = target_id if scope == "agent"   else None
            project_id   = target_id if scope == "project" else None
            results      = mem_mgr.get_memory_for_context(
                scopes     = [scope],
                agent_id   = agent_id,
                project_id = project_id,
                min_importance = min_imp,
            )
            return json.dumps({
                "scope":   scope,
                "records": results.get(scope, []),
                "count":   len(results.get(scope, [])),
            }, indent=2, default=str)

        elif tool_name == "jarvis_apply_memory_decay":
            mem_mgr      = MemoryManager(db)
            decay_factor = arguments.get("decay_factor", 0.9)
            updated      = mem_mgr.apply_memory_decay(decay_factor=decay_factor)
            return json.dumps({
                "decay_factor":   decay_factor,
                "records_updated": updated,
            }, indent=2)

        # ── JOBS & QUEUE ─────────────────────────────────────────────────────
        elif tool_name == "jarvis_submit_background_job":
            job_mgr = JobManager(db)
            job = job_mgr.submit_job(JobCreate(
                task        = arguments["task"],
                agent_id    = arguments.get("agent_id"),
                workflow_id = arguments.get("workflow_id"),
                project_id  = arguments.get("project_id"),
                priority    = arguments.get("priority", 0),
            ))
            return json.dumps({
                "job_id":           job.id,
                "status":           job.status,
                "queue_message_id": job.queue_message_id,
            }, indent=2)

        elif tool_name == "jarvis_list_jobs":
            job_mgr = JobManager(db)
            limit   = arguments.get("limit", 20)
            jobs    = job_mgr.list_jobs()
            if arguments.get("status"):
                jobs = [j for j in jobs if j.status == arguments["status"]]
            jobs = jobs[:limit]
            return json.dumps([
                {
                    "id":         j.id,
                    "job_type":   j.job_type,
                    "status":     j.status,
                    "priority":   j.priority,
                    "attempts":   j.attempts,
                    "created_at": str(j.created_at),
                }
                for j in jobs
            ], indent=2)

        elif tool_name == "jarvis_get_job":
            job_mgr  = JobManager(db)
            job      = job_mgr.get_job(arguments["job_id"])
            if not job:
                return f"Error: Job '{arguments['job_id']}' not found."
            attempts = job_mgr.get_job_attempts(job.id)
            return json.dumps({
                "id":           job.id,
                "job_type":     job.job_type,
                "status":       job.status,
                "priority":     job.priority,
                "attempts":     job.attempts,
                "max_attempts": job.max_attempts,
                "error":        job.error if hasattr(job, "error") else None,
                "metadata":     job.metadata_info,
                "created_at":   str(job.created_at),
                "completed_at": str(job.completed_at) if job.completed_at else None,
                "attempt_history": [
                    {
                        "attempt_number":     a.attempt_number,
                        "status":             a.status,
                        "latency_ms":         a.execution_latency_ms,
                        "error_message":      a.error_message,
                    }
                    for a in attempts
                ],
            }, indent=2, default=str)

        elif tool_name == "jarvis_cancel_job":
            job_mgr = JobManager(db)
            job     = job_mgr.cancel_job(arguments["job_id"])
            return json.dumps({
                "job_id": job.id,
                "status": job.status,
            }, indent=2)

        # ── SETTINGS ─────────────────────────────────────────────────────────
        elif tool_name == "jarvis_list_settings":
            settings_svc = SettingsService(db)
            items        = settings_svc.list_settings(category=arguments.get("category"))
            return json.dumps([
                {
                    "key":         s.key,
                    "value":       s.value if not s.is_secret else "***",
                    "category":    s.category,
                    "data_type":   s.data_type,
                    "description": s.description,
                }
                for s in items
            ], indent=2)

        elif tool_name == "jarvis_set_setting":
            settings_svc = SettingsService(db)
            setting      = settings_svc.set_setting(AppSettingCreate(
                key         = arguments["key"],
                value       = arguments["value"],
                category    = arguments.get("category", "general"),
                data_type   = arguments.get("data_type", "string"),
                description = arguments.get("description"),
            ))
            return json.dumps({
                "id":       setting.id,
                "key":      setting.key,
                "value":    setting.value,
                "category": setting.category,
            }, indent=2)

        # ── SECURITY & AUDIT ─────────────────────────────────────────────────
        elif tool_name == "jarvis_query_audit_logs":
            limit = arguments.get("limit", 20)
            q     = db.query(AuditEvent)
            if arguments.get("decision"):
                q = q.filter(AuditEvent.decision == arguments["decision"])
            if arguments.get("agent_id"):
                q = q.filter(AuditEvent.agent_id == arguments["agent_id"])
            if arguments.get("tool_name"):
                q = q.filter(AuditEvent.tool_name == arguments["tool_name"])
            events = q.order_by(AuditEvent.timestamp.desc()).limit(limit).all()
            return json.dumps([
                {
                    "id":        e.id,
                    "actor":     e.actor,
                    "action":    e.action,
                    "tool_name": e.tool_name,
                    "agent_id":  e.agent_id,
                    "decision":  e.decision,
                    "timestamp": str(e.timestamp),
                }
                for e in events
            ], indent=2)

        else:
            return f"Error: Unknown tool '{tool_name}'."

    except Exception as e:
        return f"Error executing tool '{tool_name}': {str(e)}"
    finally:
        db.close()


# ---------------------------------------------------------------------------
# MCP JSON-RPC stdio transport
# ---------------------------------------------------------------------------

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
                    "serverInfo": {"name": "jarvis-mcp-server", "version": "2.0.0"}
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
            name        = params.get("name")
            args        = params.get("arguments", {})
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
