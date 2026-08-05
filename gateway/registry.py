import asyncio
import sys
import time
from typing import Any

from gateway.audit import AuditLogger
from gateway.collision import CollisionRegistry
from gateway.config import get_settings, load_yaml
from gateway.mcp_client import MCPDownstreamClient
from gateway.rate_limit import RateLimiter
from gateway.rbac import RBACPolicy
from gateway.semantic_search import SemanticToolSearch


class GatewayRegistry:
    def __init__(self):
        settings = get_settings()
        config = load_yaml("config/gateway.yaml")
        self._separator = config.get("gateway", {}).get("namespace_separator", ".")
        self._top_k = config.get("gateway", {}).get("semantic_top_k", settings.semantic_top_k)
        self._server_configs = config.get("downstream_servers", [])
        self._clients: dict[str, MCPDownstreamClient] = {}
        self._collision = CollisionRegistry(separator=self._separator)
        self._tools: list[dict[str, Any]] = []
        self._tool_index: dict[str, dict] = {}
        self._semantic = SemanticToolSearch()
        self._rbac = RBACPolicy.load()
        self._audit = AuditLogger()
        self._rate_limiter = RateLimiter()
        self._connected = False
        self._sessions: dict[str, Any] = {}

    async def connect_all(self) -> dict:
        results = {"servers": [], "total_tools": 0, "collisions": []}
        all_tools = []
        for cfg in self._server_configs:
            command = cfg["command"]
            if command in ("python", "python3"):
                command = sys.executable
            client = MCPDownstreamClient(
                server_id=cfg["id"],
                command=command,
                args=cfg["args"],
                namespace=cfg["namespace"],
            )
            self._clients[cfg["id"]] = client
            ctx = client.connect()
            session = await ctx.__aenter__()
            self._sessions[cfg["id"]] = (ctx, session)
            raw_tools = await client.list_tools()
            namespaced = []
            for tool in raw_tools:
                nt = self._collision.namespace_tool(tool, cfg["id"], cfg["namespace"])
                namespaced.append(nt)
                self._tool_index[nt["name"]] = {
                    **nt,
                    "server_id": cfg["id"],
                    "original_name": tool["name"],
                }
            all_tools.extend(namespaced)
            results["servers"].append({
                "id": cfg["id"],
                "namespace": cfg["namespace"],
                "tool_count": len(namespaced),
            })
        self._tools = all_tools
        self._semantic.index_tools(all_tools)
        results["total_tools"] = len(all_tools)
        results["collisions"] = self._collision.get_collisions()
        self._connected = True
        return results

    async def disconnect_all(self) -> None:
        for server_id, (ctx, _) in list(self._sessions.items()):
            try:
                await ctx.__aexit__(None, None, None)
            except Exception:
                pass
        self._sessions.clear()
        self._connected = False

    def get_all_tools(self) -> list[dict]:
        return list(self._tools)

    def search_tools(self, query: str, top_k: int | None = None) -> list[dict]:
        k = top_k or self._top_k
        return self._semantic.search(query, top_k=k)

    def get_tools_for_context(self, query: str | None = None, top_k: int | None = None) -> list[dict]:
        if query:
            return self.search_tools(query, top_k)
        return self.get_all_tools()

    async def invoke_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        caller: str,
    ) -> dict[str, Any]:
        start = time.monotonic()
        allowed, reason = self._rbac.is_allowed(caller, tool_name)
        if not allowed:
            await self._audit.record(caller, tool_name, arguments, "denied", reason)
            return {"success": False, "error": reason, "decision": "denied"}

        rate_ok, rate_reason = self._rate_limiter.check(caller, tool_name)
        if not rate_ok:
            await self._audit.record(caller, tool_name, arguments, "rate_limited", rate_reason)
            return {"success": False, "error": rate_reason, "decision": "rate_limited"}

        resolved = self._collision.resolve(tool_name)
        if not resolved:
            tool_meta = self._tool_index.get(tool_name)
            if not tool_meta:
                await self._audit.record(caller, tool_name, arguments, "denied", "unknown tool")
                return {"success": False, "error": "unknown tool", "decision": "denied"}
            server_id = tool_meta["server_id"]
            original_name = tool_meta["original_name"]
        else:
            server_id, _, original_name = resolved

        client = self._clients.get(server_id)
        if not client:
            await self._audit.record(caller, tool_name, arguments, "denied", "server not connected")
            return {"success": False, "error": "server not connected", "decision": "denied"}

        try:
            result = await client.call_tool(original_name, arguments)
            duration_ms = (time.monotonic() - start) * 1000
            preview = result[:200] if result else ""
            await self._audit.record(
                caller, tool_name, arguments, "allowed", reason,
                duration_ms=duration_ms, result_preview=preview,
            )
            return {"success": True, "result": result, "decision": "allowed", "duration_ms": duration_ms}
        except Exception as exc:
            duration_ms = (time.monotonic() - start) * 1000
            await self._audit.record(
                caller, tool_name, arguments, "error", str(exc),
                duration_ms=duration_ms,
            )
            return {"success": False, "error": str(exc), "decision": "error"}

    @property
    def audit(self) -> AuditLogger:
        return self._audit

    @property
    def rbac(self) -> RBACPolicy:
        return self._rbac

    @property
    def semantic(self) -> SemanticToolSearch:
        return self._semantic

    @property
    def collision(self) -> CollisionRegistry:
        return self._collision

    @property
    def rate_limiter(self) -> RateLimiter:
        return self._rate_limiter

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def tool_count(self) -> int:
        return len(self._tools)


_registry: GatewayRegistry | None = None


def get_registry() -> GatewayRegistry:
    global _registry
    if _registry is None:
        _registry = GatewayRegistry()
    return _registry
