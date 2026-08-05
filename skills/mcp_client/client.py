import asyncio
import os
import shutil
import sys
from contextlib import asynccontextmanager
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class MCPDownstreamClient:
    def __init__(
        self,
        server_id: str,
        command: str,
        args: list[str],
        namespace: str,
        env: dict[str, str] | None = None,
    ):
        self.server_id = server_id
        self.command = command
        self.args = args
        self.namespace = namespace
        self.env = env or {}
        self._session: ClientSession | None = None
        self._healthy = False

    @staticmethod
    def resolve_command(command: str) -> str:
        if command in ("python", "python3"):
            return sys.executable
        if command in ("npx", "node"):
            found = shutil.which(command)
            if found:
                return found
        return command

    @asynccontextmanager
    async def connect(self):
        settings_root = os.environ.get("MCP_GATEWAY_ROOT", os.getcwd())
        env = os.environ.copy()
        env["PYTHONPATH"] = settings_root + os.pathsep + env.get("PYTHONPATH", "")
        for key, value in self.env.items():
            if value:
                env[key] = value
        cmd = self.resolve_command(self.command)
        params = StdioServerParameters(command=cmd, args=self.args, env=env)
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                self._session = session
                self._healthy = True
                yield self
                self._session = None
                self._healthy = False

    async def health_check(self) -> dict[str, Any]:
        try:
            tools = await self.list_tools()
            return {"server_id": self.server_id, "healthy": True, "tool_count": len(tools)}
        except Exception as exc:
            return {"server_id": self.server_id, "healthy": False, "error": str(exc)}

    async def list_tools(self) -> list[dict[str, Any]]:
        if not self._session:
            raise RuntimeError(f"Not connected to server {self.server_id}")
        result = await self._session.list_tools()
        tools = []
        for tool in result.tools:
            schema = {}
            if hasattr(tool, "inputSchema") and tool.inputSchema:
                schema = tool.inputSchema if isinstance(tool.inputSchema, dict) else {}
            tools.append({
                "name": tool.name,
                "description": tool.description or "",
                "inputSchema": schema,
            })
        return tools

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> str:
        if not self._session:
            raise RuntimeError(f"Not connected to server {self.server_id}")
        result = await self._session.call_tool(name, arguments)
        parts = []
        for content in result.content:
            if hasattr(content, "text"):
                parts.append(content.text)
            else:
                parts.append(str(content))
        return "\n".join(parts) if parts else ""

    @property
    def is_healthy(self) -> bool:
        return self._healthy
