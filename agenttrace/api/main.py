from fastapi import FastAPI

from agenttrace.db.database import get_connection
from agenttrace.db.repository import insert_span
from agenttrace.models.trace import SpanCreate, SpanStatus

app = FastAPI(title="AgentTrace")


def ensure_trace_exists(span: SpanCreate) -> None:
    connection = get_connection()
    try:
        trace_row = connection.execute(
            "SELECT 1 FROM traces WHERE trace_id = ?",
            (span.trace_id,),
        ).fetchone()

        if trace_row is not None:
            return

        connection.execute(
            """
            INSERT INTO traces (
                trace_id, root_span_id, agent_name, agent_version,
                started_at, ended_at, status, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                span.trace_id,
                span.parent_span_id or span.span_id,
                "unknown-agent",
                "unknown",
                span.started_at.isoformat(),
                span.ended_at.isoformat() if span.ended_at else None,
                span.status.value,
                '{}',
            ),
        )
        connection.commit()
    finally:
        connection.close()


@app.post("/v1/spans")
def create_span(span: SpanCreate):
    ensure_trace_exists(span)
    insert_span(span)
    return {"status": "ok", "span_id": span.span_id}