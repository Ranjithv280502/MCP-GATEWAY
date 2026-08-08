from pathlib import Path

from mcp.server.mcpserver import MCPServer

mcp = MCPServer("filesystem-local")

ROOT = Path(__file__).resolve().parent.parent.parent / "data" / "workspace"


def _safe_path(rel: str) -> Path:
    target = (ROOT / rel).resolve()
    if not str(target).startswith(str(ROOT.resolve())):
        raise ValueError("Path escapes workspace root")
    return target


@mcp.tool()
def read_text_file(path: str) -> str:
    """Read a text file from the local workspace."""
    return _safe_path(path).read_text(encoding="utf-8")


@mcp.tool()
def list_directory(path: str = ".") -> str:
    """List files in a workspace directory."""
    p = _safe_path(path)
    if not p.is_dir():
        return f"Not a directory: {path}"
    entries = sorted(x.name + ("/" if x.is_dir() else "") for x in p.iterdir())
    return "\n".join(entries) if entries else "(empty)"


def main():
    mcp.run()


if __name__ == "__main__":
    main()
