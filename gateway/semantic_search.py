import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

from gateway.config import get_settings


class SemanticToolSearch:
    def __init__(self, model_name: str | None = None):
        settings = get_settings()
        self._model_name = model_name or settings.embedding_model
        self._model = None
        self._tools: list[dict[str, Any]] = []
        self._embeddings: np.ndarray | None = None
        self._use_tfidf = False
        self._tfidf_vectorizer = None
        self._cache_path = settings.project_root / "data" / "embeddings" / "tool_embeddings.npz"

    def _load_model(self):
        if self._model is not None or self._use_tfidf:
            return
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self._model_name)
        except Exception:
            from sklearn.feature_extraction.text import TfidfVectorizer
            self._use_tfidf = True
            self._tfidf_vectorizer = TfidfVectorizer(max_features=512, stop_words="english")

    def _tool_text(self, tool: dict) -> str:
        name = tool.get("name", "")
        desc = tool.get("description", "") or ""
        schema = tool.get("inputSchema", {})
        props = schema.get("properties", {})
        prop_names = " ".join(props.keys()) if props else ""
        return f"{name}. {desc}. {prop_names}".strip()

    def index_tools(self, tools: list[dict[str, Any]], force_rebuild: bool = False) -> None:
        self._tools = tools
        if not force_rebuild and self._try_load_cache(tools):
            return
        self._load_model()
        texts = [self._tool_text(t) for t in tools]
        if self._use_tfidf:
            self._embeddings = self._tfidf_vectorizer.fit_transform(texts).toarray()
        else:
            self._embeddings = np.array(self._model.encode(texts, show_progress_bar=False))
        self._save_cache(tools)

    def _tools_hash(self, tools: list[dict]) -> str:
        payload = json.dumps([t.get("name") for t in tools], sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest()[:16]

    def _try_load_cache(self, tools: list[dict]) -> bool:
        if not self._cache_path.exists():
            return False
        try:
            data = np.load(self._cache_path, allow_pickle=True)
            if str(data["hash"]) != self._tools_hash(tools):
                return False
            self._embeddings = data["embeddings"]
            self._use_tfidf = bool(data.get("use_tfidf", False))
            if self._use_tfidf:
                from sklearn.feature_extraction.text import TfidfVectorizer
                self._tfidf_vectorizer = TfidfVectorizer(max_features=512, stop_words="english")
                texts = [self._tool_text(t) for t in tools]
                self._tfidf_vectorizer.fit(texts)
            return True
        except Exception:
            return False

    def _save_cache(self, tools: list[dict]) -> None:
        self._cache_path.parent.mkdir(parents=True, exist_ok=True)
        np.savez(
            self._cache_path,
            embeddings=self._embeddings,
            hash=self._tools_hash(tools),
            use_tfidf=self._use_tfidf,
        )

    def _encode_query(self, query: str) -> np.ndarray:
        self._load_model()
        if self._use_tfidf:
            return self._tfidf_vectorizer.transform([query]).toarray()[0]
        return self._model.encode([query], show_progress_bar=False)[0]

    def search(self, query: str, top_k: int = 8) -> list[dict[str, Any]]:
        if not self._tools or self._embeddings is None:
            return []
        query_vec = self._encode_query(query)
        norms = np.linalg.norm(self._embeddings, axis=1) * np.linalg.norm(query_vec)
        norms = np.where(norms == 0, 1e-10, norms)
        scores = np.dot(self._embeddings, query_vec) / norms
        top_indices = np.argsort(scores)[::-1][:top_k]
        results = []
        for idx in top_indices:
            tool = dict(self._tools[idx])
            tool["relevance_score"] = float(scores[idx])
            results.append(tool)
        return results

    def estimate_token_savings(self, top_k: int = 8) -> dict:
        if not self._tools:
            return {"all_tools_tokens": 0, "filtered_tokens": 0, "reduction_factor": 1.0}
        all_text = " ".join(self._tool_text(t) for t in self._tools)
        filtered_text = " ".join(self._tool_text(t) for t in self._tools[:top_k])
        all_tokens = len(all_text.split())
        filtered_tokens = len(filtered_text.split()) if top_k < len(self._tools) else all_tokens
        if self._tools:
            avg_tool_tokens = all_tokens / len(self._tools)
            filtered_tokens = int(avg_tool_tokens * top_k)
            all_tokens = int(avg_tool_tokens * len(self._tools))
        factor = all_tokens / max(filtered_tokens, 1)
        return {
            "total_tools": len(self._tools),
            "top_k": top_k,
            "all_tools_tokens": all_tokens,
            "filtered_tokens": filtered_tokens,
            "reduction_factor": round(factor, 1),
        }
