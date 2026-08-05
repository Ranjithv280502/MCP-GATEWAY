import asyncio
import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from gateway.config import get_settings


@dataclass
class AuditEntry:
    id: str
    timestamp: str
    caller: str
    tool_name: str
    arguments: dict[str, Any]
    decision: str
    reason: str
    duration_ms: float | None = None
    result_preview: str | None = None
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))


class AuditLogger:
    def __init__(self, log_path: Path | None = None):
        settings = get_settings()
        self._log_path = log_path or (settings.project_root / settings.audit_log_dir / settings.audit_log_file)
        self._lock = asyncio.Lock()
        self._buffer: list[AuditEntry] = []
        self._log_path.parent.mkdir(parents=True, exist_ok=True)

    async def record(
        self,
        caller: str,
        tool_name: str,
        arguments: dict[str, Any],
        decision: str,
        reason: str,
        duration_ms: float | None = None,
        result_preview: str | None = None,
    ) -> AuditEntry:
        entry = AuditEntry(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc).isoformat(),
            caller=caller,
            tool_name=tool_name,
            arguments=arguments,
            decision=decision,
            reason=reason,
            duration_ms=duration_ms,
            result_preview=result_preview,
        )
        async with self._lock:
            self._buffer.append(entry)
            line = json.dumps(asdict(entry), default=str)
            with open(self._log_path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        return entry

    async def query(
        self,
        caller: str | None = None,
        tool_name: str | None = None,
        decision: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        async with self._lock:
            entries = []
            if self._log_path.exists():
                with open(self._log_path, encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            entries.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
            if caller:
                entries = [e for e in entries if e.get("caller") == caller]
            if tool_name:
                entries = [e for e in entries if e.get("tool_name") == tool_name]
            if decision:
                entries = [e for e in entries if e.get("decision") == decision]
            return entries[-limit:]

    def stats(self) -> dict:
        if not self._log_path.exists():
            return {"total": 0, "allowed": 0, "denied": 0, "rate_limited": 0}
        allowed = denied = rate_limited = 0
        with open(self._log_path, encoding="utf-8") as f:
            for line in f:
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                d = entry.get("decision", "")
                if d == "allowed":
                    allowed += 1
                elif d == "denied":
                    denied += 1
                elif d == "rate_limited":
                    rate_limited += 1
        return {
            "total": allowed + denied + rate_limited,
            "allowed": allowed,
            "denied": denied,
            "rate_limited": rate_limited,
        }
