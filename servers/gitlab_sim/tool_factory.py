def build_gitlab_tools(mcp):
    @mcp.tool()
    def create_issue(project: str, title: str, description: str = "") -> str:
        return f"Created GitLab issue in {project}: {title}"

    @mcp.tool()
    def list_issues(project: str, state: str = "opened") -> str:
        return f"Listed {state} issues for GitLab project {project}"

    @mcp.tool()
    def create_merge_request(project: str, source_branch: str, target_branch: str = "main") -> str:
        return f"Created MR {source_branch} -> {target_branch} in {project}"

    @mcp.tool()
    def search_repositories(query: str) -> str:
        return f"GitLab repo search: 3 results for '{query}'"

    @mcp.tool()
    def get_file_contents(project: str, file_path: str, ref: str = "main") -> str:
        return f"GitLab file {file_path}@{ref} from {project}"

    @mcp.tool()
    def create_branch(project: str, branch: str, ref: str = "main") -> str:
        return f"Created branch {branch} from {ref} in {project}"

    @mcp.tool()
    def list_commits(project: str, branch: str = "main") -> str:
        return f"Listed commits on {branch} for {project}"

    @mcp.tool()
    def push_files(project: str, branch: str, files: str) -> str:
        return f"Pushed files to {project}/{branch}"

    @mcp.tool()
    def create_repository(name: str, visibility: str = "private") -> str:
        return f"Created GitLab repository {name} ({visibility})"

    @mcp.tool()
    def fork_repository(project: str, namespace: str = "") -> str:
        return f"Forked GitLab project {project}"
