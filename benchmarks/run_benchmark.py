import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ["MCP_GATEWAY_ROOT"] = str(Path(__file__).resolve().parent.parent)

from benchmarks.naive_baseline import naive_keyword_pick, naive_top_k_pick
from gateway.config import ensure_data_dirs
from gateway.registry import get_registry
from gateway.semantic_search import SemanticToolSearch


def naive_select(all_tools: list[dict], query: str, expected: list[str]) -> bool:
    pick = naive_keyword_pick(all_tools, query)
    if pick in expected:
        return True
    top8 = naive_top_k_pick(all_tools, query, top_k=8)
    return any(e in top8 for e in expected)


def semantic_select(search: SemanticToolSearch, query: str, expected: list[str], top_k: int = 8) -> bool:
    results = search.search(query, top_k=top_k)
    found = {t["name"] for t in results}
    return any(e in found for e in expected)


def rank_hit_position(search: SemanticToolSearch, query: str, expected: list[str], top_k: int = 8) -> int | None:
    results = search.search(query, top_k=top_k)
    names = [t["name"] for t in results]
    best_rank = None
    for exp in expected:
        if exp in names:
            rank = names.index(exp) + 1
            if best_rank is None or rank < best_rank:
                best_rank = rank
    return best_rank


async def run_benchmark():
    ensure_data_dirs()
    registry = get_registry()
    print("Connecting to downstream MCP servers...")
    info = await registry.connect_all()
    print(f"Loaded {info['total_tools']} tools from {len(info['servers'])} servers")
    if info.get("collisions"):
        print(f"Resolved {len(info['collisions'])} name collision(s)")

    queries_path = Path(__file__).parent / "queries.json"
    with open(queries_path, encoding="utf-8") as f:
        queries = json.load(f)

    all_tools = registry.get_all_tools()
    search = registry.semantic
    top_k = 8

    naive_hits = 0
    semantic_hits = 0
    ranks = []

    print(f"\nRunning benchmark on {len(queries)} queries (top_k={top_k})...\n")
    print(f"{'Query':<55} {'Naive':>6} {'Semantic':>9} {'Rank':>5}")
    print("-" * 80)

    for item in queries:
        query = item["query"]
        expected = item["expected_tools"]
        naive_ok = naive_select(all_tools, query, expected)
        sem_ok = semantic_select(search, query, expected, top_k)
        rank = rank_hit_position(search, query, expected, top_k)
        if naive_ok:
            naive_hits += 1
        if sem_ok:
            semantic_hits += 1
        if rank:
            ranks.append(rank)
        q_short = query[:52] + "..." if len(query) > 55 else query
        print(f"{q_short:<55} {'Y' if naive_ok else 'N':>6} {'Y' if sem_ok else 'N':>9} {rank or '-':>5}")

    total = len(queries)
    naive_acc = naive_hits / total * 100
    sem_acc = semantic_hits / total * 100
    avg_rank = sum(ranks) / len(ranks) if ranks else 0
    savings = search.estimate_token_savings(top_k)

    print("\n" + "=" * 80)
    print("BENCHMARK RESULTS")
    print("=" * 80)
    print(f"Total queries:              {total}")
    print(f"Total tools registered:     {len(all_tools)}")
    print(f"Semantic top-K:             {top_k}")
    print(f"Naive accuracy (all tools): {naive_acc:.1f}% ({naive_hits}/{total})")
    print(f"Semantic accuracy (top-{top_k}):  {sem_acc:.1f}% ({semantic_hits}/{total})")
    print(f"Avg rank of first hit:      {avg_rank:.1f}")
    print(f"Token reduction factor:     {savings['reduction_factor']}x")
    print(f"Est. all-tools tokens:      {savings['all_tools_tokens']}")
    print(f"Est. filtered tokens:       {savings['filtered_tokens']}")
    print("=" * 80)
    print(f"\nMetric: Tool-selection accuracy {naive_acc:.0f}% -> {sem_acc:.0f}% with semantic filtering;")
    print(f"        tool-definition tokens cut {savings['reduction_factor']}x.")

    results = {
        "total_queries": total,
        "total_tools": len(all_tools),
        "top_k": top_k,
        "naive_accuracy_pct": round(naive_acc, 1),
        "semantic_accuracy_pct": round(sem_acc, 1),
        "avg_first_hit_rank": round(avg_rank, 2),
        "token_savings": savings,
    }
    out_path = Path(__file__).parent / "results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {out_path}")

    await registry.disconnect_all()


if __name__ == "__main__":
    asyncio.run(run_benchmark())
