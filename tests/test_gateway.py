import asyncio
import pytest

from gateway.collision import CollisionRegistry
from gateway.rate_limit import RateLimiter
from gateway.rbac import RBACPolicy


def test_collision_namespacing():
    reg = CollisionRegistry(separator=".")
    n1 = reg.register("server_a", "schema", "validate_record")
    n2 = reg.register("server_b", "data", "validate_record")
    assert n1 == "schema.validate_record"
    assert n2 == "data.validate_record"
    assert reg.resolve(n1) == ("server_a", "schema", "validate_record")


def test_collision_duplicate_resolution():
    reg = CollisionRegistry(separator=".")
    reg.register("s1", "ns", "validate_record")
    n2 = reg.register("s2", "ns", "validate_record")
    assert n2 == "ns.validate_record_2"
    assert len(reg.get_collisions()) == 1


def test_rbac_wildcard_admin():
    policy = RBACPolicy(
        roles={"admin": {"allowed_tools": ["*"]}},
        users={"admin@test.com": {"roles": ["admin"]}},
    )
    ok, reason = policy.is_allowed("admin@test.com", "anything.tool")
    assert ok is True


def test_rbac_developer_pattern():
    policy = RBACPolicy(
        roles={"developer": {"allowed_tools": ["schema.*", "data.search_*"]}},
        users={"dev@test.com": {"roles": ["developer"]}},
    )
    ok, _ = policy.is_allowed("dev@test.com", "schema.validate_user")
    assert ok is True
    ok, _ = policy.is_allowed("dev@test.com", "workflow.run_workflow")
    assert ok is False


def test_rbac_denied_no_roles():
    policy = RBACPolicy(roles={}, users={"nobody@test.com": {"roles": []}})
    ok, reason = policy.is_allowed("nobody@test.com", "any.tool")
    assert ok is False
    assert "no roles" in reason


def test_rate_limiter_allows_burst():
    limiter = RateLimiter.__new__(RateLimiter)
    limiter._default = __import__("gateway.rate_limit", fromlist=["RateLimitConfig"]).RateLimitConfig(
        requests_per_minute=60, burst=5
    )
    limiter._per_tool = {}
    limiter._buckets = {}
    for _ in range(5):
        ok, _ = limiter.check("user1", "test.tool")
        assert ok is True


def test_rate_limiter_blocks_after_burst():
    limiter = RateLimiter.__new__(RateLimiter)
    limiter._default = __import__("gateway.rate_limit", fromlist=["RateLimitConfig"]).RateLimitConfig(
        requests_per_minute=60, burst=2
    )
    limiter._per_tool = {}
    limiter._buckets = {}
    limiter.check("user2", "test.tool")
    limiter.check("user2", "test.tool")
    ok, reason = limiter.check("user2", "test.tool")
    assert ok is False
    assert "rate limit" in reason


@pytest.mark.asyncio
async def test_audit_logger_concurrent_writes(tmp_path):
    from gateway.audit import AuditLogger
    log_file = tmp_path / "audit.jsonl"
    logger = AuditLogger(log_path=log_file)

    async def write_entry(i):
        await logger.record(f"user{i % 3}", f"tool_{i}", {"arg": i}, "allowed", "test")

    await asyncio.gather(*[write_entry(i) for i in range(20)])
    entries = await logger.query(limit=50)
    assert len(entries) == 20
    callers = {e["caller"] for e in entries}
    assert len(callers) >= 1


def test_semantic_search_basic():
    from gateway.semantic_search import SemanticToolSearch
    search = SemanticToolSearch()
    tools = [
        {"name": "schema.validate_user", "description": "Validate User record against schema"},
        {"name": "analytics.calculate_mrr", "description": "Calculate monthly recurring revenue"},
        {"name": "workflow.trigger_webhook", "description": "Trigger webhook delivery to endpoint"},
    ]
    search.index_tools(tools, force_rebuild=True)
    results = search.search("validate user record schema", top_k=2)
    assert len(results) >= 1
    top = results[0]["name"].lower() + results[0].get("description", "").lower()
    assert "user" in top or "schema" in top or "validate" in top
