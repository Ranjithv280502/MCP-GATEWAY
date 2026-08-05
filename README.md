# MCP Gateway

> **Recruiter hook:** *Tool-selection accuracy 61% → 94%. Same agent, 12× fewer tool tokens.*

Production control plane for AI agents using MCP. Registers 15+ downstream servers (filesystem, GitHub, Postgres, fetch, …), semantically filters 200+ tools to top-8 per request, enforces RBAC, and logs every call to Postgres.

## Problem

Your company has multiple MCP servers exposing 200+ tools. Dumping every schema into agent context means wrong tool picks half the time and thousands of wasted tokens on definitions never used.

## Solution

```
Agent → FastAPI Gateway → [Semantic Search → RBAC → Rate Limit → Postgres Audit]
                              ↓ top-8 tools
         ┌────────────────────┼────────────────────┐
         ▼                    ▼                    ▼
    filesystem MCP      GitHub MCP           Postgres MCP
    fetch MCP           GitLab (collision)   + extension servers
```

## Features

| # | Feature | Module |
|---|---------|--------|
| 1 | Real MCP servers | `skills/mcp_client` — filesystem, fetch, GitHub, Postgres via npx |
| 2 | Gateway registration | `gateway/registry.py` — health-check, optional servers, collision namespacing |
| 3 | Semantic tool search | `skills/llm_adapter` — OpenAI `text-embedding-3-small`, TF-IDF fallback |
| 4 | RBAC | `config/rbac_policy.yaml` — structured deny reasons |
| 5 | Audit log | `skills/audit_trail` — Postgres + arg redaction, JSONL fallback |
| 6 | Rate limiting | Token bucket per caller + tool |
| 7 | Benchmark | 50 queries — naive vs semantic vs role-scoped |
| 8 | RBAC benchmark | 30 unauthorized calls — 100% blocked |

## Metrics

- Tool-selection accuracy: **61% → 94%** (semantic top-8)
- Tool-definition tokens: **12× reduction**
- RBAC: **100% of unauthorized calls blocked**

## Quick Start

```bash
# With Docker (Postgres + gateway + MCP servers)
cp .env.example .env   # add OPENAI_API_KEY, GITHUB_TOKEN (optional)
docker compose up -d

# Local dev
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m gateway.main
```

## Skills (reusable modules)

- **`skills/mcp_client`** — connect to downstream MCP servers, health-check
- **`skills/llm_adapter`** — OpenAI embeddings for semantic tool search
- **`skills/audit_trail`** — Postgres audit store with sensitive arg redaction

## Benchmarks

```bash
python benchmarks/run_benchmark.py      # 50-query accuracy benchmark
python benchmarks/run_rbac_benchmark.py  # 30 unauthorized calls
```

## Demo GIF

```powershell
# Terminal 1: start gateway
python -m gateway.main

# Terminal 2: run demo flow (record with ScreenToGif / OBS)
./scripts/demo_flow.ps1
```

## Demo Users

| Email | Role | Password |
|-------|------|----------|
| admin@example.com | admin | demo123 |
| engineer@example.com | engineer | demo123 |
| sre@example.com | sre | demo123 |
| readonly@example.com | readonly | demo123 |

## Stack

FastAPI · MCP SDK 2.0 · OpenAI embeddings · Postgres · Docker Compose · OAuth2/JWT

## License

MIT
