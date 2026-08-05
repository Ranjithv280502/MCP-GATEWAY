import asyncio
import json
import os
from typing import Any

from mcp.server.mcpserver import MCPServer

from gateway.config import ensure_data_dirs, get_settings
from gateway.registry import get_registry

os.environ.setdefault("MCP_GATEWAY_ROOT", str(get_settings().project_root))

mcp = MCPServer("mcp-gateway")
_session_query: str = ""
_session_caller: str = "mcp-agent"


async def _ensure_connected():
    registry = get_registry()
    if not registry.is_connected:
        ensure_data_dirs()
        await registry.connect_all()
    return registry


@mcp.tool()
async def search_tools(query: str, top_k: int = 8) -> str:
    registry = await _ensure_connected()
    results = registry.search_tools(query, top_k)
    payload = [{"name": t["name"], "score": round(t.get("relevance_score", 0), 4),
                "description": t.get("description", "")[:120]} for t in results]
    return json.dumps({"query": query, "top_k": top_k, "tools": payload}, indent=2)


@mcp.tool()
async def list_relevant_tools(user_query: str) -> str:
    global _session_query
    _session_query = user_query
    registry = await _ensure_connected()
    results = registry.search_tools(user_query, top_k=8)
    return json.dumps([t["name"] for t in results])


@mcp.tool()
async def call_gateway_tool(tool_name: str, arguments: str = "{}") -> str:
    registry = await _ensure_connected()
    try:
        args = json.loads(arguments) if arguments else {}
    except json.JSONDecodeError:
        return json.dumps({"error": "arguments must be valid JSON"})
    result = await registry.invoke_tool(tool_name, args, _session_caller)
    return json.dumps(result, indent=2)


@mcp.tool()
async def gateway_status() -> str:
    registry = await _ensure_connected()
    return json.dumps({
        "connected": registry.is_connected,
        "tool_count": registry.tool_count,
        "collisions": len(registry.collision.get_collisions()),
        "audit_stats": registry.audit.stats(),
    })


def main():
    mcp.run()


if __name__ == "__main__":
    main()
