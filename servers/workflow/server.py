from mcp.server.mcpserver import MCPServer
from servers.workflow.tool_factory import build_workflow_tools

mcp = MCPServer("workflow")
build_workflow_tools(mcp)


def main():
    mcp.run()


if __name__ == "__main__":
    main()
