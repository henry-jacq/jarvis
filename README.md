# Jarvis

> **A Secure, Context-Aware Agent Runtime & Orchestration Platform**

Jarvis is a self-hosted agent control plane designed to run AI agents securely while keeping persistent state outside the agents themselves.

---

## ⚡ Core Architecture & Principles

- **Stateless Agents, Persistent State**: Persistent memory, configuration, projects, conversations, workflows, executions, and jobs are stored centrally in MySQL. Agents only receive a bounded `ExecutionContext` for each invocation.
- **No Direct DB Access**: Agents never receive database credentials or raw SQL access. All state retrieval is mediated by trusted services (*Context Builder*, *Memory Manager*, *Permission Engine*, *Queue Service*, *Workflow Service*).
- **Dynamic Workflows & Human-in-the-Loop (HITL)**: Multi-agent static & dynamic workflows with conditional edge routing (`condition_expression`), `human_approval` pause interrupts (`WAITING_FOR_APPROVAL`), and checkpoint resume handlers.
- **Zero-Trust Permission Engine**: Tools are gated outside model reasoning using runtime permission policies (`ALLOW`, `DENY`, `REVIEW`), creating interactive approval requests on `REVIEW` policy hits.
- **Generic DB Queue & Asynchronous Workers**: Primary durable queue (`queue_messages` table) stores generic work payloads decoupled from specific entity schemas, with atomic claiming (`claim_next_message`), backoff retries, and optional secondary Redis dispatch (`REDIS_URL`).
- **Conversations & Long-Lived Project Workspaces**: Standalone conversations can evolve into long-lived Projects containing objectives, tasks, documents, research, and execution history.
- **System App Settings (`app_settings`) & Workflow Limits**: Centralized system settings store enforcing `MAX_WORKFLOW_DEPTH` (3), `MAX_NODES` (20), `MAX_PARALLEL_BRANCHES` (5).

---

## 🏗 System Architecture

```text
Client / API Request
        │
   FastAPI V1
        │
┌───────┴─────────────────────────────────────────┐
│                                                 │
SimpleAgentExecutor / StaticWorkflowExecutor  JobManager / Scheduler
│                                                 │
Context Builder & Workflow Compiler         Generic DB Queue (queue_messages)
│                                                 │
Memory / App Settings / Workflows           Worker Engine (Async)
Project / Conversations / Checkpoints             │
(MySQL System of Record)                    Permission Engine (Gated Tools)
│                                                 │
└───────┬─────────────────────────────────────────┘
        │
   LangGraph Harness
        │
 Unified LLM Provider (Ollama / Cloud Models)
        │
 Execution Results, Node Checkpoints & HITL Approvals
```

---

## 🚀 Quickstart

### 1. Environment Setup
```bash
# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\activate  # Windows (or source venv/bin/activate on Linux/macOS)

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment
Copy `.env.example` to `.env` and set your MySQL database connection string, server host/port, and optional Redis URL:
```bash
cp .env.example .env
```
Default MySQL: `DATABASE_URL=mysql+pymysql://root:password@localhost:3306/jarvis`
Default Server: `HOST=0.0.0.0`, `PORT=8000`

### 3. Initialize & Seed Database
Auto-create database tables and seed system settings, project workspace, generic queue payloads, demo agents, multi-agent static workflow, HITL dynamic workflow, background job, and recurring schedule:
```bash
python scripts/seed_demo.py
```

### 4. Run API Server & Background Worker
Launch the FastAPI control plane:
```bash
python main.py
```
To run a standalone background worker:
```bash
python -m app.runtime.worker
```
Access interactive API docs at [http://localhost:8000/docs](http://localhost:8000/docs).

---

## 🧪 Running Tests

Run the 22-test suite covering background workflow job execution, memory decay/eviction, vector retrieval stubs, dynamic workflows, HITL pause/resume flow, `REVIEW` tool policy gating, graph validation, multi-agent execution, checkpointing, generic queue operations, background job retries, cron scheduling, context building, memory management, and conversations:
```bash
pytest -v
```


---

## 📌 API Overview

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/api/v1/settings` | `POST / GET` | System App Settings management |
| `/api/v1/conversations` | `POST / GET` | Manage conversations, append messages, and evaluate project suggestions |
| `/api/v1/projects` | `POST / GET` | Register projects, objectives, tasks, documents, and attached conversations |
| `/api/v1/agents` | `POST / GET` | Manage agents and publish version snapshots |
| `/api/v1/workflows` | `POST / GET` | Create workflows, publish versions, execute multi-agent pipelines, and retrieve checkpoints |
| `/api/v1/executions/approvals/pending` | `GET` | List pending Human-in-the-Loop & tool execution approval requests |
| `/api/v1/executions/{id}/approvals/{approval_id}/decision` | `POST` | Submit human approval/rejection decision and resume execution |
| `/api/v1/queue` | `POST / GET` | Enqueue generic payloads (`queue_messages`) and inspect primary DB queue status |
| `/api/v1/jobs` | `POST / GET` | Submit background jobs (`/submit`), cancel jobs, and inspect attempt telemetry |
| `/api/v1/schedules` | `POST / GET` | Create recurring schedules (`cron`/`interval`) and trigger manual evaluations |
| `/api/v1/memory/candidate` | `POST` | Propose memory candidates (Global, Agent, Project) |
| `/api/v1/tools` | `GET` | List registered tools and risk levels |
| `/api/v1/executions/submit` | `POST` | Trigger synchronous single-agent execution |


