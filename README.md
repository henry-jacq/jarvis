# Jarvis

> **A Secure, Context-Aware Agent Runtime & Orchestration Platform**

Jarvis is a self-hosted agent control plane designed to run AI agents securely while keeping persistent state outside the agents themselves.

---

## ⚡ Core Architecture & Principles

- **Stateless Agents, Persistent State**: Persistent memory, configuration, projects, conversations, and state are stored centrally in MySQL. Agents only receive a bounded `ExecutionContext` for each invocation.
- **No Direct DB Access**: Agents never receive database credentials or raw SQL access. All state retrieval is mediated by trusted services (*Context Builder*, *Memory Manager*, *Permission Engine*).
- **Zero-Trust Permission Engine**: Tools are gated outside model reasoning using runtime permission policies (`ALLOW`, `DENY`, `REVIEW`).
- **Conversations & Long-Lived Project Workspaces**: Standalone conversations can evolve into long-lived Projects containing objectives, tasks, documents, research, and execution history.
- **System App Settings (`app_settings`)**: Centralized system settings store replacing single-tenant application abstractions.

---

## 🏗 System Architecture

```text
Client / API Request
        │
   FastAPI V1
        │
 SimpleAgentExecutor
        │
   ┌────┴──────────────────────────┐
   │                               │
 Context Builder             Permission Engine
   │                               │
 Memory / App Settings       Tool Registry (Gated)
 Project / Conversations           │
 (MySQL System of Record)          │
   │                               │
   └────┬──────────────────────────┘
        │
   LangGraph Harness
        │
 Unified LLM Provider
 (Ollama / Cloud Models)
        │
 Execution Results & Audit Logs
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
Copy `.env.example` to `.env` and set your MySQL database connection string, server host/port, and model endpoints:
```bash
cp .env.example .env
```
Default connection: `DATABASE_URL=mysql+pymysql://root:password@localhost:3306/jarvis`
Default server: `HOST=0.0.0.0`, `PORT=8000`

### 3. Initialize & Seed Database
Auto-create database tables and seed system settings, project workspace, and demo conversation:
```bash
python scripts/seed_demo.py
```

### 4. Run API Server Directly
You can launch the platform directly using Python:
```bash
python main.py
```
Or via uvicorn:
```bash
uvicorn main:app --reload
```
Access interactive API docs at [http://localhost:8000/docs](http://localhost:8000/docs).

---

## 🧪 Running Tests

Run the full test suite covering permission policies, context building, memory management, conversations, app settings, and agent execution flows:
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
| `/api/v1/memory/candidate` | `POST` | Propose memory candidates (Global, Agent, Project) |
| `/api/v1/tools` | `GET` | List registered tools and risk levels |
| `/api/v1/executions/submit` | `POST` | Trigger agent execution with token & event tracking |
| `/api/v1/executions/{id}/events` | `GET` | View execution telemetry & step-by-step audit logs |
