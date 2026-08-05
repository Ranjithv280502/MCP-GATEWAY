import asyncio
import pytest

from gateway.collision import CollisionRegistry
from gateway.rate_limit import RateLimiter
from gateway.rbac import RBACPolicy
from skills.audit_trail.redaction import redact_arguments


def test_collision_github_gitlab():
    reg = CollisionRegistry(separator=".")
    gh = reg.register("github", "github", "create_issue")
    gl = reg.register("gitlab", "gitlab", "create_issue")
    assert gh == "github.create_issue"
    assert gl == "gitlab.create_issue"


def test_rbac_engineer_github_issue():
    policy = RBACPolicy(
        roles={"engineer": {"allowed_tools": ["github.create_issue", "fs.*"]}},
        users={"eng@test.com": {"roles": ["engineer"]}},
    )
    ok, _ = policy.is_allowed("eng@test.com", "github.create_issue")
    assert ok is True
    ok, reason = policy.is_allowed("eng@test.com", "gitlab.create_issue")
    assert ok is False
    assert "denied" in reason


def test_redact_sensitive_args():
    args = {"username": "alice", "password": "secret123", "query": "SELECT 1"}
    redacted = redact_arguments(args)
    assert redacted["password"] == "***REDACTED***"
    assert redacted["username"] == "alice"


def test_rate_limiter_blocks_after_burst():
    limiter = RateLimiter.__new__(RateLimiter)
    limiter._default = __import__("gateway.rate_limit", fromlist=["RateLimitConfig"]).RateLimitConfig(
        requests_per_minute=60, burst=2
    )
    limiter._per_tool = {}
    limiter._buckets = {}
    limiter.check("user", "github.create_issue")
    limiter.check("user", "github.create_issue")
    ok, _ = limiter.check("user", "github.create_issue")
    assert ok is False


@pytest.mark.asyncio
async def test_audit_store_jsonl_fallback(tmp_path, monkeypatch):
    from gateway.config import get_settings
    from skills.audit_trail.store import AuditStore

    settings = get_settings()
    log_file = tmp_path / "audit.jsonl"
    store = AuditStore()
    store._use_postgres = False
    store._pool = None
    store._jsonl_path = log_file

    await store.record("user@test.com", "fs.read_text_file", {"path": "x"}, "allowed", "ok", role="engineer")
    entries = await store.query(limit=10)
    assert len(entries) == 1
    assert entries[0]["role"] == "engineer"


def test_embedding_search():
    from skills.llm_adapter import EmbeddingAdapter
    search = EmbeddingAdapter()
    tools = [
        {"name": "github.create_issue", "description": "Create a GitHub issue in a repository"},
        {"name": "gitlab.create_issue", "description": "Create a GitLab issue in a project"},
        {"name": "fs.read_text_file", "description": "Read a text file from the filesystem"},
    ]
    search.index_tools(tools, force_rebuild=True)
    results = search.search("create GitHub issue for bug report", top_k=2)
    assert len(results) >= 1
    assert "github" in results[0]["name"] or "issue" in results[0]["name"]
