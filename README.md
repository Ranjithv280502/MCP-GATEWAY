# MCP Gateway

A production-style infrastructure layer between AI agents and MCP tool servers. When an agent has 200+ tools, dumping every schema into context hurts accuracy and cost — this gateway aggregates downstream servers into one surface with **semantic tool search**, **RBAC**, **audit logging**, and **rate limiting**.

> **Tool-selection accuracy ~61% → ~94%** with semantic top-8 filtering. **Tool-definition tokens cut ~12×.**

Built with FastAPI, MCP SDK, sentence-transformers, and OAuth2/JWT. No UI required — agents connect via MCP protocol or REST API. Ideal as a portfolio project for GitHub and LinkedIn.

## Architecture

```
┌─────────────┐     ┌──────────────────────────────────────────────┐
│  AI Agent   │────▶│              MCP Gateway (FastAPI)            │
│  (Cursor)   │     │  ┌─────────┐ ┌────────┐ ┌───────┐ ┌────────┐ │
└─────────────┘     │  │Semantic │ │  RBAC  │ │ Audit │ │ Rate   │ │
                    │  │ Search  │ │ Policy │ │  Log  │ │ Limit  │ │
                    │  └────┬────┘ └────────┘ └───────┘ └────────┘ │
                    │       │ top-8 relevant tools                    │
                    └───────┼──────────────────────────────────────────┘
                            │
          ┌─────────────────┼─────────────────┬─────────────────┐
          ▼                 ▼                 ▼                 ▼
   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
   │  Schema     │  │  Data Ops   │  │  Analytics  │  │  Workflow   │
   │  Validation │  │  CRUD/Search│  │  Metrics    │  │  Automation │
   └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘
```

## Features

| Feature | Description |
|---------|-------------|
| Multi-server aggregation | Registers 4 downstream MCP servers as one unified surface |
| Semantic tool search | Embeds tool descriptions; returns top-8 most relevant at request time |
| Per-tool RBAC | YAML policy maps roles → allowed tool patterns; rejects unauthorized calls |
| Audit log | Every call logged with caller, args, timestamp, allow/deny (concurrent-safe) |
| Name collision handling | Namespaces tools (`schema.validate_user`) with auto-suffix on conflicts |
| Rate limiting | Token-bucket per caller + tool |
| Benchmark suite | Compares naive keyword selection vs semantic retrieval on labeled queries |

## Quick Start

```bash
git clone https://github.com/yourusername/mcp-gateway.git
cd mcp-gateway
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env

python -m gateway.main             # REST API on :8080
python benchmarks/run_benchmark.py # accuracy benchmark
pytest tests/ -v
```

## API

| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/token` | OAuth2 password grant → JWT |
| POST | `/tools/search` | Semantic search → top-K tools |
| POST | `/tools/call` | Invoke tool through gateway |
| GET | `/audit` | Query audit log |
| GET | `/health` | Health check |

```bash
# Authenticate (demo password: demo123)
TOKEN=$(curl -s -X POST http://localhost:8080/auth/token \
  -d "username=dev@example.com&password=demo123" | jq -r .access_token)

# Semantic tool search
curl -s -X POST http://localhost:8080/tools/search \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "validate User record against strict schema", "top_k": 8}' | jq

# Call a tool
curl -s -X POST http://localhost:8080/tools/call \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "schema.validate_user", "arguments": {"payload": "{\"type\":\"User\",\"id\":\"u1\",\"name\":\"Jane\"}"}}' | jq
```

## Demo Users

| Email | Role | Password |
|-------|------|----------|
| admin@example.com | admin | demo123 |
| dev@example.com | developer | demo123 |
| analyst@example.com | analyst | demo123 |
| ops@example.com | operator | demo123 |

## MCP Agent Integration

```json
{
  "mcpServers": {
    "mcp-gateway": {
      "command": "python",
      "args": ["-m", "gateway.mcp_server"],
      "env": {
        "MCP_GATEWAY_ROOT": "/path/to/mcp-gateway",
        "PYTHONPATH": "/path/to/mcp-gateway"
      }
    }
  }
}
```

## Project Structure

```
mcp-gateway/
├── config/              # Gateway, RBAC, rate limit policies
├── gateway/             # Core: registry, semantic search, auth, audit
├── servers/             # Example downstream MCP servers (swap for your domain)
│   ├── schema_validation/
│   ├── data_ops/
│   ├── analytics/
│   └── workflow/
├── benchmarks/          # Tool-selection accuracy benchmark
└── tests/
```

Downstream servers use generic entity types (User, Order, Product, etc.) as **examples**. Replace them with your own domain tools — the gateway layer stays the same.

## Stack

FastAPI · MCP SDK · sentence-transformers · OAuth2/JWT · YAML policies

## License

MIT
