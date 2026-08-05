import os
import time
from typing import Any

from gateway.collision import CollisionRegistry
from gateway.config import get_settings, load_yaml
from gateway.rate_limit import RateLimiter
from gateway.rbac import RBACPolicy
from skills.audit_trail import AuditStore
from skills.llm_adapter import EmbeddingAdapter
from skills.mcp_client import MCPDownstreamClient


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
        self._semantic = EmbeddingAdapter()
        self._rbac = RBACPolicy.load()
        self._audit = AuditStore()
        self._rate_limiter = RateLimiter()
        self._connected = False
        self._sessions: dict[str, Any] = {}
        self._server_health: list[dict] = []

    def _resolve_server_config(self, cfg: dict) -> dict:
        settings = get_settings()
        args = []
        for arg in cfg.get("args", []):
            if arg == "./data/workspace":
                args.append(str(settings.project_root / "data" / "workspace"))
            elif "${POSTGRES_MCP_URL}" in str(arg) or arg == settings.postgres_mcp_url:
                args.append(settings.postgres_mcp_url)
            else:
                args.append(str(arg).replace("${POSTGRES_MCP_URL}", settings.postgres_mcp_url))
        env = {}
        for key, val in (cfg.get("env") or {}).items():
            expanded = val.replace("${GITHUB_TOKEN}", settings.github_token or os.environ.get("GITHUB_TOKEN", ""))
            if expanded:
                env[key] = expanded
        return {**cfg, "args": args, "env": env}

    async def connect_all(self) -> dict:
        await self._audit.initialize()
        results = {"servers": [], "total_tools": 0, "collisions": [], "skipped": []}
        all_tools = []
        for raw_cfg in self._server_configs:
            cfg = self._resolve_server_config(raw_cfg)
            optional = cfg.get("optional", False)
            if cfg["id"] == "github" and not cfg.get("env", {}).get("GITHUB_PERSONAL_ACCESS_TOKEN"):
                if optional:
                    results["skipped"].append({"id": cfg["id"], "reason": "GITHUB_TOKEN not set"})
                    continue
            if cfg["id"] == "postgres" and not os.environ.get("POSTGRES_MCP_URL") and optional:
                try:
                    import asyncpg
                    conn = await asyncpg.connect(get_settings().postgres_mcp_url, timeout=2)
                    await conn.close()
                except Exception:
                    results["skipped"].append({"id": cfg["id"], "reason": "Postgres not reachable"})
                    continue
            client = MCPDownstreamClient(
                server_id=cfg["id"],
                command=cfg["command"],
                args=cfg["args"],
                namespace=cfg["namespace"],
                env=cfg.get("env"),
            )
            ctx = None
            try:
                ctx = client.connect()
                session = await ctx.__aenter__()
                self._clients[cfg["id"]] = client
                self._sessions[cfg["id"]] = (ctx, session)
                raw_tools = await client.list_tools()
                health = await client.health_check()
                self._server_health.append(health)
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
                    "healthy": health.get("healthy", True),
                })
            except Exception as exc:
                if ctx is not None:
                    try:
                        await ctx.__aexit__(None, None, None)
                    except Exception:
                        pass
                if optional:
                    results["skipped"].append({"id": cfg["id"], "reason": str(exc)})
                else:
                    raise
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
        await self._audit.close()
        self._connected = False

    def get_all_tools(self) -> list[dict]:
        return list(self._tools)

    def get_allowed_tool_names(self, email: str) -> set[str]:
        allowed = set()
        for tool in self._tools:
            ok, _ = self._rbac.is_allowed(email, tool["name"])
            if ok:
                allowed.add(tool["name"])
        return allowed

    def search_tools(self, query: str, top_k: int | None = None, caller: str | None = None) -> list[dict]:
        k = top_k or self._top_k
        allowed = self.get_allowed_tool_names(caller) if caller else None
        return self._semantic.search(query, top_k=k, allowed_names=allowed)

    async def invoke_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        caller: str,
        roles: list[str] | None = None,
    ) -> dict[str, Any]:
        start = time.monotonic()
        role_str = ",".join(roles) if roles else None
        allowed, reason = self._rbac.is_allowed(caller, tool_name)
        if not allowed:
            await self._audit.record(
                caller, tool_name, arguments, "denied", reason, role=role_str,
            )
            return {"success": False, "error": reason, "decision": "denied", "deny_reason": reason}

        rate_ok, rate_reason = self._rate_limiter.check(caller, tool_name)
        if not rate_ok:
            await self._audit.record(
                caller, tool_name, arguments, "rate_limited", rate_reason, role=role_str,
            )
            return {"success": False, "error": rate_reason, "decision": "rate_limited"}

        resolved = self._collision.resolve(tool_name)
        if not resolved:
            tool_meta = self._tool_index.get(tool_name)
            if not tool_meta:
                await self._audit.record(
                    caller, tool_name, arguments, "denied", "unknown tool", role=role_str,
                )
                return {"success": False, "error": "unknown tool", "decision": "denied"}
            server_id = tool_meta["server_id"]
            original_name = tool_meta["original_name"]
        else:
            server_id, _, original_name = resolved

        client = self._clients.get(server_id)
        if not client:
            await self._audit.record(
                caller, tool_name, arguments, "denied", "server not connected", role=role_str,
            )
            return {"success": False, "error": "server not connected", "decision": "denied"}

        try:
            result = await client.call_tool(original_name, arguments)
            duration_ms = (time.monotonic() - start) * 1000
            preview = result[:200] if result else ""
            await self._audit.record(
                caller, tool_name, arguments, "allowed", reason,
                role=role_str, duration_ms=duration_ms, result_preview=preview,
            )
            return {"success": True, "result": result, "decision": "allowed", "duration_ms": duration_ms}
        except Exception as exc:
            duration_ms = (time.monotonic() - start) * 1000
            await self._audit.record(
                caller, tool_name, arguments, "error", str(exc),
                role=role_str, duration_ms=duration_ms,
            )
            return {"success": False, "error": str(exc), "decision": "error"}

    @property
    def audit(self) -> AuditStore:
        return self._audit

    @property
    def rbac(self) -> RBACPolicy:
        return self._rbac

    @property
    def semantic(self) -> EmbeddingAdapter:
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

    @property
    def server_health(self) -> list[dict]:
        return list(self._server_health)


_registry: GatewayRegistry | None = None


def get_registry() -> GatewayRegistry:
    global _registry
    if _registry is None:
        _registry = GatewayRegistry()
    return _registry
