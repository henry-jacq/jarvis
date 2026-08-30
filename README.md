# Jarvis

> **A Secure, Context-Aware Agent Runtime & Orchestration Platform**

Jarvis is a self-hosted agent control plane designed to run AI agents securely while keeping persistent state outside the agents themselves.

---

## ⚡ Core Invariants

- **Stateless Agents, Persistent State**: Persistent memory, configuration, and state are stored centrally in MySQL. Agents only receive a bounded `ExecutionContext` for each invocation.
- **No Direct DB Access**: Agents never receive database credentials or raw SQL access. All state retrieval is mediated by trusted services (*Context Builder*, *Memory Manager*, *Permission Engine*).
- **Bounded Authority & Zero-Trust Enforcement**: Tools are gated outside model reasoning using runtime permission policies (`ALLOW`, `DENY`, `REVIEW`).
- **Reproducible Executions**: Every execution references immutable agent versions, prompt layers, and model configurations.

---

## 🏗 System Architecture

```text
User / API Request
        │
   FastAPI V1
        │
 SimpleAgentExecutor
        │
   ┌────┴──────────────────────────┐
   │                               │
 Context Builder             Permission Engine
   │                               │
 Memory / MySQL              Tool Registry (Gated)
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
Copy `.env.example` to `.env` and set your MySQL database connection string and model endpoints:
```bash
cp .env.example .env
```
Default connection: `DATABASE_URL=mysql+pymysql://root:password@localhost:3306/jarvis`

### 3. Initialize & Seed Database
Auto-create database tables and seed demo entities:
```bash
python scripts/seed_demo.py
```

### 4. Run API Server
```bash
uvicorn app.main:app --reload
```
Access interactive API docs at [http://localhost:8000/docs](http://localhost:8000/docs).

---

## 🧪 Running Tests

Run the test suite covering permission policies, context building, memory management, and agent execution flows:
```bash
pytest -v
```

---

## 📌 API Overview

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/api/v1/applications` | `POST / GET` | Create and list applications |
| `/api/v1/projects` | `POST / GET` | Register projects and structured context |
| `/api/v1/agents` | `POST / GET` | Manage agents and publish version snapshots |
| `/api/v1/memory/candidate` | `POST` | Propose memory candidates (Global, Agent, Project) |
| `/api/v1/tools` | `GET` | List registered tools and risk levels |
| `/api/v1/executions/submit` | `POST` | Trigger agent execution with token & event tracking |
| `/api/v1/executions/{id}/events` | `GET` | View execution telemetry & step-by-step audit logs |
