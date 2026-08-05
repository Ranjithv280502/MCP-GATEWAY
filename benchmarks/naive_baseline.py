import re
from typing import Any


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def keyword_score(query: str, tool: dict[str, Any]) -> float:
    q_tokens = _tokenize(query)
    tool_text = f"{tool.get('name', '')} {tool.get('description', '')}"
    t_tokens = _tokenize(tool_text)
    if not q_tokens or not t_tokens:
        return 0.0
    overlap = q_tokens & t_tokens
    return len(overlap) / len(q_tokens)


def naive_keyword_pick(all_tools: list[dict], query: str) -> str | None:
    if not all_tools:
        return None
    scored = [(keyword_score(query, t), t["name"]) for t in all_tools]
    scored.sort(reverse=True)
    return scored[0][1]


def naive_top_k_pick(all_tools: list[dict], query: str, top_k: int = 8) -> list[str]:
    scored = [(keyword_score(query, t), t["name"]) for t in all_tools]
    scored.sort(reverse=True)
    return [name for _, name in scored[:top_k]]
