from mcp.server.mcpserver import MCPServer

mcp = MCPServer("postgres-sim")


@mcp.tool()
def query(sql: str) -> str:
    """Run a read-only SQL query against the demo database."""
    sql_lower = sql.lower()
    if "vendor" in sql_lower:
        return "id | name | status\n42 | Acme | pending_review"
    return "rows: 1 (demo postgres-sim)"


def main():
    mcp.run()


if __name__ == "__main__":
    main()
