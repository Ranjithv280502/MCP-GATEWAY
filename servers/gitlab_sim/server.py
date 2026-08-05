from mcp.server.mcpserver import MCPServer
from servers.gitlab_sim.tool_factory import build_gitlab_tools

mcp = MCPServer("gitlab-sim")
build_gitlab_tools(mcp)


def main():
    mcp.run()


if __name__ == "__main__":
    main()
