from mcp.server.mcpserver import MCPServer
from servers.schema_validation.tool_factory import build_validation_tools

mcp = MCPServer("schema-validation")
build_validation_tools(mcp)


def main():
    mcp.run()


if __name__ == "__main__":
    main()
