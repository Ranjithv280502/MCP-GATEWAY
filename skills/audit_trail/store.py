import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from gateway.config import get_settings
from skills.audit_trail.redaction import redact_arguments


class AuditStore:
    def __init__(self):
        settings = get_settings()
        self._pg_dsn = settings.postgres_dsn
        self._pool = None
        self._jsonl_path = settings.project_root / settings.audit_log_dir / settings.audit_log_file
        self._jsonl_path.parent.mkdir(parents=True, exist_ok=True)
        self._use_postgres = bool(self._pg_dsn)

    async def initialize(self) -> None:
        if not self._use_postgres:
            return
        try:
            import asyncpg
            self._pool = await asyncpg.create_pool(self._pg_dsn, min_size=1, max_size=5)
            async with self._pool.acquire() as conn:
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS audit_log (
                        id UUID PRIMARY KEY,
                        timestamp TIMESTAMPTZ NOT NULL,
                        caller TEXT NOT NULL,
                        role TEXT,
                        tool_name TEXT NOT NULL,
                        arguments JSONB NOT NULL,
                        decision TEXT NOT NULL,
                        reason TEXT NOT NULL,
                        duration_ms DOUBLE PRECISION,
                        result_preview TEXT,
                        request_id UUID NOT NULL
                    )
                """)
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_audit_caller ON audit_log(caller)
                """)
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_audit_decision ON audit_log(decision)
                """)
        except Exception:
            self._use_postgres = False
            self._pool = None

    async def close(self) -> None:
        if self._pool:
            await self._pool.close()

    async def record(
        self,
        caller: str,
        tool_name: str,
        arguments: dict[str, Any],
        decision: str,
        reason: str,
        role: str | None = None,
        duration_ms: float | None = None,
        result_preview: str | None = None,
    ) -> dict:
        entry_id = str(uuid.uuid4())
        request_id = str(uuid.uuid4())
        ts = datetime.now(timezone.utc)
        safe_args = redact_arguments(arguments)
        entry = {
            "id": entry_id,
            "timestamp": ts.isoformat(),
            "caller": caller,
            "role": role,
            "tool_name": tool_name,
            "arguments": safe_args,
            "decision": decision,
            "reason": reason,
            "duration_ms": duration_ms,
            "result_preview": result_preview,
            "request_id": request_id,
        }
        if self._use_postgres and self._pool:
            async with self._pool.acquire() as conn:
                await conn.execute(
                    """INSERT INTO audit_log
                       (id, timestamp, caller, role, tool_name, arguments, decision, reason, duration_ms, result_preview, request_id)
                       VALUES ($1,$2,$3,$4,$5,$6::jsonb,$7,$8,$9,$10,$11)""",
                    uuid.UUID(entry_id), ts, caller, role, tool_name,
                    json.dumps(safe_args), decision, reason, duration_ms, result_preview, uuid.UUID(request_id),
                )
        else:
            with open(self._jsonl_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, default=str) + "\n")
        return entry

    async def query(
        self,
        caller: str | None = None,
        tool_name: str | None = None,
        decision: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        if self._use_postgres and self._pool:
            clauses = []
            params: list[Any] = []
            idx = 1
            if caller:
                clauses.append(f"caller = ${idx}")
                params.append(caller)
                idx += 1
            if tool_name:
                clauses.append(f"tool_name = ${idx}")
                params.append(tool_name)
                idx += 1
            if decision:
                clauses.append(f"decision = ${idx}")
                params.append(decision)
                idx += 1
            where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
            params.append(limit)
            sql = f"SELECT * FROM audit_log {where} ORDER BY timestamp DESC LIMIT ${idx}"
            async with self._pool.acquire() as conn:
                rows = await conn.fetch(sql, *params)
            return [dict(r) for r in rows]
        entries = []
        if self._jsonl_path.exists():
            with open(self._jsonl_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            entries.append(json.loads(line))
                        except json.JSONDecodeError:
                            pass
        if caller:
            entries = [e for e in entries if e.get("caller") == caller]
        if tool_name:
            entries = [e for e in entries if e.get("tool_name") == tool_name]
        if decision:
            entries = [e for e in entries if e.get("decision") == decision]
        return entries[-limit:]

    async def stats(self) -> dict:
        if self._use_postgres and self._pool:
            async with self._pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT
                        COUNT(*) AS total,
                        COUNT(*) FILTER (WHERE decision = 'allowed') AS allowed,
                        COUNT(*) FILTER (WHERE decision = 'denied') AS denied,
                        COUNT(*) FILTER (WHERE decision = 'rate_limited') AS rate_limited
                    FROM audit_log
                """)
            return dict(row) if row else {"total": 0, "allowed": 0, "denied": 0, "rate_limited": 0}
        stats = {"total": 0, "allowed": 0, "denied": 0, "rate_limited": 0}
        if not self._jsonl_path.exists():
            return stats
        with open(self._jsonl_path, encoding="utf-8") as f:
            for line in f:
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                stats["total"] += 1
                d = entry.get("decision", "")
                if d in stats:
                    stats[d] += 1
        return stats
