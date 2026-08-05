import asyncio
import os
import sys
from contextlib import asynccontextmanager
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class MCPDownstreamClient:
    def __init__(self, server_id: str, command: str, args: list[str], namespace: str):
        self.server_id = server_id
        self.command = command
        self.args = args
        self.namespace = namespace
        self._session: ClientSession | None = None
        self._exit_stack = None

    @asynccontextmanager
    async def connect(self):
        settings_root = os.environ.get("MCP_GATEWAY_ROOT", os.getcwd())
        env = os.environ.copy()
        env["PYTHONPATH"] = settings_root + os.pathsep + env.get("PYTHONPATH", "")
        params = StdioServerParameters(command=self.command, args=self.args, env=env)
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                self._session = session
                yield self
                self._session = None

    async def list_tools(self) -> list[dict[str, Any]]:
        if not self._session:
            raise RuntimeError(f"Not connected to server {self.server_id}")
        result = await self._session.list_tools()
        tools = []
        for tool in result.tools:
            tools.append({
                "name": tool.name,
                "description": tool.description or "",
                "inputSchema": tool.inputSchema if hasattr(tool, "inputSchema") else {},
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
