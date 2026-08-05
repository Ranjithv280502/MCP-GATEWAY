from mcp.server.mcpserver import MCPServer
from servers.data_ops.tool_factory import build_data_tools

mcp = MCPServer("data-ops")
build_data_tools(mcp)


def main():
    mcp.run()


if __name__ == "__main__":
    main()
