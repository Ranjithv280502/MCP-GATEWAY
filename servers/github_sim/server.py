from mcp.server.mcpserver import MCPServer

mcp = MCPServer("github-sim")


@mcp.tool()
def create_issue(owner: str, repo: str, title: str, body: str = "") -> str:
    """Create a GitHub issue in a repository."""
    return f"https://github.com/{owner}/{repo}/issues/101 — {title}"


@mcp.tool()
def list_issues(owner: str, repo: str, state: str = "open") -> str:
    """List GitHub issues for a repository."""
    return f"Issues ({state}) in {owner}/{repo}: #101 Review vendor contract"


def main():
    mcp.run()


if __name__ == "__main__":
    main()
