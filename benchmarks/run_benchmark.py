import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ["MCP_GATEWAY_ROOT"] = str(Path(__file__).resolve().parent.parent))

from benchmarks.naive_baseline import naive_top_k_pick
from gateway.config import ensure_data_dirs
from gateway.registry import get_registry


def naive_select(all_tools, query, expected, top_k=8):
    names = naive_top_k_pick(all_tools, query, top_k)
    return any(e in names for e in expected)


def semantic_select(search, query, expected, top_k=8, allowed=None):
    results = search.search(query, top_k=top_k, allowed_names=allowed)
    found = {t["name"] for t in results}
    return any(e in found for e in expected)


def role_scoped_select(registry, email, query, expected, top_k=8):
    allowed = registry.get_allowed_tool_names(email)
    results = registry.semantic.search(query, top_k=top_k, allowed_names=allowed)
    found = {t["name"] for t in results}
    return any(e in found for e in expected)


async def run_benchmark():
    ensure_data_dirs()
    registry = get_registry()
    print("Connecting to downstream MCP servers...")
    info = await registry.connect_all()
    print(f"Loaded {info['total_tools']} tools from {len(info['servers'])} servers")
    if info.get("skipped"):
        print(f"Skipped optional servers: {info['skipped']}")
    if info.get("collisions"):
        print(f"Resolved {len(info['collisions'])} name collision(s)")

    queries_path = Path(__file__).parent / "queries.json"
    with open(queries_path, encoding="utf-8") as f:
        queries = json.load(f)

    all_tools = registry.get_all_tools()
    search = registry.semantic
    top_k = 8
    role_email = "engineer@example.com"

    naive_hits = semantic_hits = role_hits = 0

    print(f"\nRunning benchmark on {len(queries)} queries (top_k={top_k})...\n")
    print(f"{'Query':<50} {'Naive':>6} {'Semantic':>9} {'Role':>6}")
    print("-" * 78)

    for item in queries:
        query = item["query"]
        expected = item["expected_tools"]
        naive_ok = naive_select(all_tools, query, expected, top_k)
        sem_ok = semantic_select(search, query, expected, top_k)
        role_ok = role_scoped_select(registry, role_email, query, expected, top_k)
        if naive_ok:
            naive_hits += 1
        if sem_ok:
            semantic_hits += 1
        if role_ok:
            role_hits += 1
        q_short = query[:47] + "..." if len(query) > 50 else query
        print(f"{q_short:<50} {'Y' if naive_ok else 'N':>6} {'Y' if sem_ok else 'N':>9} {'Y' if role_ok else 'N':>6}")

    total = len(queries)
    naive_acc = naive_hits / total * 100
    sem_acc = semantic_hits / total * 100
    role_acc = role_hits / total * 100
    savings = search.estimate_token_savings(top_k)

    print("\n" + "=" * 78)
    print("BENCHMARK RESULTS")
    print("=" * 78)
    print(f"Total queries:                 {total}")
    print(f"Total tools registered:        {len(all_tools)}")
    print(f"Naive (all tools, keyword):    {naive_acc:.1f}% ({naive_hits}/{total})")
    print(f"Semantic top-{top_k}:               {sem_acc:.1f}% ({semantic_hits}/{total})")
    print(f"Semantic + role scoped:        {role_acc:.1f}% ({role_hits}/{total})")
    print(f"Token reduction factor:        {savings['reduction_factor']}x")
    print("=" * 78)
    print(f"\nRecruiter hook: Tool-selection accuracy {naive_acc:.0f}% -> {sem_acc:.0f}%;"
          f" tokens cut {savings['reduction_factor']}x.")

    results = {
        "total_queries": total,
        "total_tools": len(all_tools),
        "top_k": top_k,
        "naive_accuracy_pct": round(naive_acc, 1),
        "semantic_accuracy_pct": round(sem_acc, 1),
        "role_scoped_accuracy_pct": round(role_acc, 1),
        "token_savings": savings,
    }
    out_path = Path(__file__).parent / "results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {out_path}")
    await registry.disconnect_all()


if __name__ == "__main__":
    asyncio.run(run_benchmark())
