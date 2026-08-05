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
);

CREATE INDEX IF NOT EXISTS idx_audit_caller ON audit_log(caller);
CREATE INDEX IF NOT EXISTS idx_audit_decision ON audit_log(decision);
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp DESC);
