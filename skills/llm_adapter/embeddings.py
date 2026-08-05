import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

from gateway.config import get_settings


class EmbeddingAdapter:
    def __init__(self, model: str | None = None):
        settings = get_settings()
        self._model = model or settings.embedding_model
        self._client = None
        self._use_openai = False
        self._use_tfidf = False
        self._tfidf_vectorizer = None
        self._tools: list[dict[str, Any]] = []
        self._embeddings: np.ndarray | None = None
        self._cache_path = settings.project_root / "data" / "embeddings" / "tool_embeddings.npz"

    def _init_backend(self) -> None:
        if self._client is not None or self._use_tfidf:
            return
        settings = get_settings()
        if settings.openai_api_key:
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=settings.openai_api_key)
                self._use_openai = True
                return
            except Exception:
                pass
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            self._use_tfidf = True
            self._tfidf_vectorizer = TfidfVectorizer(max_features=512, stop_words="english")
        except Exception:
            self._use_tfidf = True
            self._tfidf_vectorizer = None

    def _tool_text(self, tool: dict) -> str:
        name = tool.get("name", "")
        desc = tool.get("description", "") or ""
        schema = tool.get("inputSchema", {})
        props = schema.get("properties", {}) if isinstance(schema, dict) else {}
        prop_names = " ".join(props.keys()) if props else ""
        return f"{name}. {desc}. {prop_names}".strip()

    def _embed_batch(self, texts: list[str]) -> np.ndarray:
        self._init_backend()
        if self._use_openai and self._client:
            response = self._client.embeddings.create(input=texts, model=self._model)
            vectors = [item.embedding for item in response.data]
            return np.array(vectors)
        if self._tfidf_vectorizer is not None:
            return self._tfidf_vectorizer.fit_transform(texts).toarray()
        from sklearn.feature_extraction.text import TfidfVectorizer
        self._tfidf_vectorizer = TfidfVectorizer(max_features=512, stop_words="english")
        return self._tfidf_vectorizer.fit_transform(texts).toarray()

    def _embed_query(self, query: str) -> np.ndarray:
        self._init_backend()
        if self._use_openai and self._client:
            response = self._client.embeddings.create(input=[query], model=self._model)
            return np.array(response.data[0].embedding)
        return self._tfidf_vectorizer.transform([query]).toarray()[0]

    def index_tools(self, tools: list[dict[str, Any]], force_rebuild: bool = False) -> None:
        self._tools = tools
        if not force_rebuild and self._try_load_cache(tools):
            return
        texts = [self._tool_text(t) for t in tools]
        self._embeddings = self._embed_batch(texts)
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
            if bool(data.get("use_tfidf", False)):
                from sklearn.feature_extraction.text import TfidfVectorizer
                self._use_tfidf = True
                self._tfidf_vectorizer = TfidfVectorizer(max_features=512, stop_words="english")
                texts = [self._tool_text(t) for t in tools]
                self._tfidf_vectorizer.fit(texts)
            return True
        except Exception:
            return False

    def _save_cache(self, tools: list[dict]) -> None:
        self._cache_path.parent.mkdir(parents=True, exist_ok=True)
        np.savez(self._cache_path, embeddings=self._embeddings, hash=self._tools_hash(tools), use_tfidf=self._use_tfidf)

    def search(self, query: str, top_k: int = 8, allowed_names: set[str] | None = None) -> list[dict[str, Any]]:
        if not self._tools or self._embeddings is None:
            return []
        query_vec = self._embed_query(query)
        norms = np.linalg.norm(self._embeddings, axis=1) * np.linalg.norm(query_vec)
        norms = np.where(norms == 0, 1e-10, norms)
        scores = np.dot(self._embeddings, query_vec) / norms
        ranked = np.argsort(scores)[::-1]
        results = []
        for idx in ranked:
            tool = self._tools[idx]
            if allowed_names is not None and tool["name"] not in allowed_names:
                continue
            item = dict(tool)
            item["relevance_score"] = float(scores[idx])
            results.append(item)
            if len(results) >= top_k:
                break
        return results

    def estimate_token_savings(self, top_k: int = 8) -> dict:
        if not self._tools:
            return {"all_tools_tokens": 0, "filtered_tokens": 0, "reduction_factor": 1.0}
        all_text = " ".join(self._tool_text(t) for t in self._tools)
        all_tokens = len(all_text.split())
        avg = all_tokens / len(self._tools)
        filtered = int(avg * top_k)
        factor = all_tokens / max(filtered, 1)
        return {
            "total_tools": len(self._tools),
            "top_k": top_k,
            "all_tools_tokens": int(all_tokens),
            "filtered_tokens": filtered,
            "reduction_factor": round(factor, 1),
        }
