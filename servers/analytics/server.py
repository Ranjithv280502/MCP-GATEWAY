from mcp.server.mcpserver import MCPServer
from servers.analytics.tool_factory import build_analytics_tools

mcp = MCPServer("analytics")
build_analytics_tools(mcp)


def main():
    mcp.run()


if __name__ == "__main__":
    main()
