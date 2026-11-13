CREATE TABLE IF NOT EXISTS traces (
    trace_id TEXT PRIMARY KEY,
    root_span_id TEXT NOT NULL,
    agent_name TEXT NOT NULL,
    agent_version TEXT NOT NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    status TEXT NOT NULL DEFAULT 'ok',
    total_input_tokens INTEGER DEFAULT 0,
    total_output_tokens INTEGER DEFAULT 0,
    total_cost_usd REAL DEFAULT 0.0,
    error_type TEXT,
    metadata_json TEXT DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS spans (
    span_id TEXT PRIMARY KEY,
    trace_id TEXT NOT NULL REFERENCES traces(trace_id),
    parent_span_id TEXT,
    name TEXT NOT NULL,
    kind TEXT NOT NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    duration_ms INTEGER,
    status TEXT NOT NULL DEFAULT 'ok',
    attributes_json TEXT DEFAULT '{}',
    input_payload_json TEXT,
    output_payload_json TEXT,
    error_type TEXT,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS span_events (
    event_id TEXT PRIMARY KEY,
    span_id TEXT NOT NULL REFERENCES spans(span_id),
    trace_id TEXT NOT NULL,
    name TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    attributes_json TEXT DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_spans_trace ON spans(trace_id);
CREATE INDEX IF NOT EXISTS idx_spans_parent ON spans(parent_span_id);
CREATE INDEX IF NOT EXISTS idx_traces_status ON traces(status, started_at);
CREATE INDEX IF NOT EXISTS idx_traces_agent ON traces(agent_name, started_at);