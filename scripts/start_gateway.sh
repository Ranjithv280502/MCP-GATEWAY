#!/usr/bin/env bash
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export MCP_GATEWAY_ROOT="$ROOT"
export PYTHONPATH="$ROOT:$PYTHONPATH"
echo "Starting MCP Gateway on http://localhost:8080"
python -m gateway.main
