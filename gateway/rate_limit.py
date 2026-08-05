import time
from collections import defaultdict, deque
from dataclasses import dataclass, field

import yaml

from gateway.config import get_settings


@dataclass
class RateLimitConfig:
    requests_per_minute: int = 60
    burst: int = 10


@dataclass
class TokenBucket:
    capacity: float
    tokens: float
    refill_rate: float
    last_refill: float = field(default_factory=time.monotonic)

    def consume(self, amount: float = 1.0) -> bool:
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now
        if self.tokens >= amount:
            self.tokens -= amount
            return True
        return False


class RateLimiter:
    def __init__(self, config_path: str = "config/rate_limits.yaml"):
        settings = get_settings()
        with open(settings.project_root / config_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        default = data.get("default", {})
        self._default = RateLimitConfig(
            requests_per_minute=default.get("requests_per_minute", 60),
            burst=default.get("burst", 10),
        )
        self._per_tool: dict[str, RateLimitConfig] = {}
        for tool_name, cfg in data.get("per_tool", {}).items():
            self._per_tool[tool_name] = RateLimitConfig(
                requests_per_minute=cfg.get("requests_per_minute", 60),
                burst=cfg.get("burst", 10),
            )
        self._buckets: dict[str, TokenBucket] = {}

    def _get_config(self, tool_name: str) -> RateLimitConfig:
        return self._per_tool.get(tool_name, self._default)

    def _get_bucket(self, key: str, config: RateLimitConfig) -> TokenBucket:
        if key not in self._buckets:
            refill_rate = config.requests_per_minute / 60.0
            self._buckets[key] = TokenBucket(
                capacity=float(config.burst),
                tokens=float(config.burst),
                refill_rate=refill_rate,
            )
        return self._buckets[key]

    def check(self, caller: str, tool_name: str) -> tuple[bool, str]:
        config = self._get_config(tool_name)
        key = f"{caller}:{tool_name}"
        bucket = self._get_bucket(key, config)
        if bucket.consume():
            return True, "within rate limit"
        retry_after = (1.0 - bucket.tokens) / bucket.refill_rate if bucket.refill_rate > 0 else 60
        return False, f"rate limit exceeded, retry after ~{retry_after:.0f}s"

    def reset(self, caller: str | None = None, tool_name: str | None = None) -> None:
        if caller is None and tool_name is None:
            self._buckets.clear()
            return
        keys_to_remove = []
        for key in self._buckets:
            c, t = key.split(":", 1)
            if (caller is None or c == caller) and (tool_name is None or t == tool_name):
                keys_to_remove.append(key)
        for key in keys_to_remove:
            del self._buckets[key]
