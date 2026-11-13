import json
from datetime import datetime

from agenttrace.db.database import get_connection
from agenttrace.models.trace import SpanCreate, TraceCreate


def _to_json(value: dict | None) -> str | None:
    if value is None:
        return None
    return json.dumps(value, default=str)


def _from_json(value: str | None) -> dict:
    if not value:
        return {}
    return json.loads(value)


def insert_trace(trace: TraceCreate, db_path: str = "agenttrace.db") -> str:
    connection = get_connection(db_path)

    try:
        connection.execute(
            """
            INSERT INTO traces (
                trace_id, root_span_id, agent_name, agent_version,
                started_at, ended_at, status, metadata_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                trace.trace_id,
                trace.root_span_id,
                trace.agent_name,
                trace.agent_version,
                trace.started_at.isoformat(),
                trace.ended_at.isoformat() if trace.ended_at else None,
                trace.status.value,
                _to_json(trace.metadata),
            ),
        )

        for span in trace.spans:
            insert_span(span, connection=connection)

        connection.commit()
        return trace.trace_id
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def insert_span(
    span: SpanCreate,
    connection=None,
    db_path: str = "agenttrace.db",
) -> str:
    owns_connection = connection is None

    if owns_connection:
        connection = get_connection(db_path)

    try:
        connection.execute(
            """
            INSERT INTO spans (
                span_id, trace_id, parent_span_id, name, kind,
                started_at, ended_at, duration_ms, status,
                attributes_json, input_payload_json, output_payload_json,
                error_type, error_message, retry_count
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                span.span_id,
                span.trace_id,
                span.parent_span_id,
                span.name,
                span.kind.value,
                span.started_at.isoformat(),
                span.ended_at.isoformat() if span.ended_at else None,
                span.duration_ms,
                span.status.value,
                _to_json(span.attributes),
                _to_json(span.input_payload),
                _to_json(span.output_payload),
                span.error_type,
                span.error_message,
                0,
            ),
        )

        if owns_connection:
            connection.commit()

        return span.span_id
    except Exception:
        if owns_connection:
            connection.rollback()
        raise
    finally:
        if owns_connection:
            connection.close()


def get_trace(trace_id: str, db_path: str = "agenttrace.db") -> dict | None:
    connection = get_connection(db_path)

    try:
        trace_row = connection.execute(
            "SELECT * FROM traces WHERE trace_id = ?",
            (trace_id,),
        ).fetchone()

        if trace_row is None:
            return None

        span_rows = connection.execute(
            "SELECT * FROM spans WHERE trace_id = ? ORDER BY started_at",
            (trace_id,),
        ).fetchall()

        return {
            **dict(trace_row),
            "metadata": _from_json(trace_row["metadata_json"]),
            "spans": [
                {
                    **dict(span_row),
                    "attributes": _from_json(span_row["attributes_json"]),
                    "input_payload": _from_json(span_row["input_payload_json"]),
                    "output_payload": _from_json(span_row["output_payload_json"]),
                }
                for span_row in span_rows
            ],
        }
    finally:
        connection.close()


def list_traces(
    status: str | None = None,
    agent_name: str | None = None,
    limit: int = 50,
    db_path: str = "agenttrace.db",
) -> list[dict]:
    query = "SELECT * FROM traces"
    conditions = []
    params: list = []

    if status:
        conditions.append("status = ?")
        params.append(status)

    if agent_name:
        conditions.append("agent_name = ?")
        params.append(agent_name)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY started_at DESC LIMIT ?"
    params.append(limit)

    connection = get_connection(db_path)

    try:
        rows = connection.execute(query, params).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()