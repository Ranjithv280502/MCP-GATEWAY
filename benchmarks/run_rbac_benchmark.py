import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ["MCP_GATEWAY_ROOT"] = str(Path(__file__).resolve().parent.parent))

from gateway.config import ensure_data_dirs
from gateway.registry import get_registry

UNAUTHORIZED_CALLS = [
    ("readonly@example.com", ["readonly"], "github.create_issue", {"owner": "o", "repo": "r", "title": "t"}),
    ("readonly@example.com", ["readonly"], "gitlab.create_issue", {"project": "p", "title": "t"}),
    ("readonly@example.com", ["readonly"], "fs.write_file", {"path": "x", "content": "y"}),
    ("readonly@example.com", ["readonly"], "workflow.trigger_webhook", {"target": "http://x"}),
    ("readonly@example.com", ["readonly"], "data.create_user", {"payload": "{}"}),
    ("readonly@example.com", ["readonly"], "postgres.query", {"sql": "SELECT 1"}),
    ("sre@example.com", ["sre"], "github.create_issue", {"owner": "o", "repo": "r", "title": "t"}),
    ("sre@example.com", ["sre"], "gitlab.create_merge_request", {"project": "p", "source_branch": "b"}),
    ("sre@example.com", ["sre"], "fs.write_file", {"path": "x", "content": "y"}),
    ("sre@example.com", ["sre"], "data.create_order", {"payload": "{}"}),
    ("engineer@example.com", ["engineer"], "workflow.run_workflow", {"workflow_id": "w1"}),
    ("engineer@example.com", ["engineer"], "analytics.calculate_mrr", {}),
    ("engineer@example.com", ["engineer"], "gitlab.create_repository", {"name": "r"}),
    ("readonly@example.com", ["readonly"], "schema.validate_batch", {"payload": "{}"}),
    ("readonly@example.com", ["readonly"], "data.bulk_export", {"entity_type": "User"}),
    ("sre@example.com", ["sre"], "data.create_product", {"payload": "{}"}),
    ("readonly@example.com", ["readonly"], "workflow.send_email", {"recipient": "a@b.com", "message": "hi"}),
    ("readonly@example.com", ["readonly"], "analytics.detect_anomaly", {"metric": "errors"}),
    ("engineer@example.com", ["engineer"], "workflow.cancel_job", {"job_id": "j1"}),
    ("sre@example.com", ["sre"], "gitlab.push_files", {"project": "p", "branch": "b", "files": "[]"}),
    ("readonly@example.com", ["readonly"], "data.patch_task", {"task_id": "t1", "patch": "{}"}),
    ("readonly@example.com", ["readonly"], "workflow.register_webhook", {"url": "http://x", "events": "e"}),
    ("sre@example.com", ["sre"], "data.delete_order", {"order_id": "o1"}),
    ("engineer@example.com", ["engineer"], "analytics.export_dashboard", {"dashboard_id": "d1"}),
    ("readonly@example.com", ["readonly"], "workflow.schedule_job", {"target": "t"}),
    ("sre@example.com", ["sre"], "github.create_pull_request", {"owner": "o", "repo": "r", "title": "t", "head": "h", "base": "main"}),
    ("readonly@example.com", ["readonly"], "data.transaction_batch", {"payload": "{}"}),
    ("engineer@example.com", ["engineer"], "workflow.pause_workflow", {"workflow_id": "w1"}),
    ("readonly@example.com", ["readonly"], "analytics.calculate_churn_rate", {}),
    ("sre@example.com", ["sre"], "gitlab.fork_repository", {"project": "p"}),
]


async def run_rbac_benchmark():
    ensure_data_dirs()
    registry = get_registry()
    print("Connecting to downstream MCP servers...")
    await registry.connect_all()

    blocked = 0
    allowed = 0
    print(f"\nRunning RBAC benchmark: {len(UNAUTHORIZED_CALLS)} unauthorized calls...\n")

    for caller, roles, tool_name, args in UNAUTHORIZED_CALLS:
        result = await registry.invoke_tool(tool_name, args, caller, roles=roles)
        if result.get("decision") == "denied":
            blocked += 1
            status = "BLOCKED"
        else:
            allowed += 1
            status = "ALLOWED"
        print(f"  {status}: {caller} -> {tool_name}")

    total = len(UNAUTHORIZED_CALLS)
    block_rate = blocked / total * 100
    print("\n" + "=" * 60)
    print(f"RBAC blocked: {blocked}/{total} ({block_rate:.1f}%)")
    print(f"Metric: RBAC blocked {block_rate:.0f}% of {total} unauthorized calls.")
    print("=" * 60)
    await registry.disconnect_all()
    return block_rate


if __name__ == "__main__":
    asyncio.run(run_rbac_benchmark())
