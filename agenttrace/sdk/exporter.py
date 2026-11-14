import httpx

from agenttrace.db.database import DEFAULT_DB_PATH, initialize_database
from agenttrace.db.repository import insert_span, insert_trace
from agenttrace.models.trace import SpanCreate, SpanKind, SpanStatus, TraceCreate
from agenttrace.sdk.context import now

API_URL = "http://127.0.0.1:8000"


def _persist_local_span(
    *,
    span_id: str,
    trace_id: str,
    parent_span_id: str | None,
    name: str,
    kind: str,
    started_at,
    ended_at,
    duration_ms: int,
    status,
    error_type: str | None = None,
    error_message: str | None = None,
    db_path: str = str(DEFAULT_DB_PATH),
) -> None:
    initialize_database(db_path)

    existing_trace = None
    try:
        from agenttrace.db.repository import get_trace

        existing_trace = get_trace(trace_id, db_path=db_path)
    except Exception:
        existing_trace = None

    if existing_trace is None:
        insert_trace(
            TraceCreate(
                trace_id=trace_id,
                root_span_id=parent_span_id or span_id,
                agent_name=name,
                agent_version="unknown",
                started_at=started_at,
                ended_at=ended_at,
                status=status if isinstance(status, SpanStatus) else SpanStatus.OK,
                metadata={},
            ),
            db_path=db_path,
        )

    insert_span(
        SpanCreate(
            span_id=span_id,
            trace_id=trace_id,
            parent_span_id=parent_span_id,
            name=name,
            kind=SpanKind(kind) if isinstance(kind, str) else kind,
            started_at=started_at,
            ended_at=ended_at,
            duration_ms=duration_ms,
            status=status if isinstance(status, SpanStatus) else SpanStatus.OK,
            attributes={},
            error_type=error_type,
            error_message=error_message,
        ),
        db_path=db_path,
    )


def export_span(
    span_id: str,
    trace_id: str,
    parent_span_id: str | None,
    name: str,
    kind: str,
    started_at,
    ended_at,
    duration_ms: int,
    status,
    error_type: str | None = None,
    error_message: str | None = None,
    db_path: str = str(DEFAULT_DB_PATH),
) -> None:
    payload = {
        "span_id": span_id,
        "trace_id": trace_id,
        "parent_span_id": parent_span_id,
        "name": name,
        "kind": kind,
        "started_at": started_at.isoformat(),
        "ended_at": ended_at.isoformat(),
        "duration_ms": duration_ms,
        "status": status.value if hasattr(status, "value") else status,
        "attributes": {},
        "error_type": error_type,
        "error_message": error_message,
    }

    try:
        response = httpx.post(
            f"{API_URL}/v1/spans",
            json=payload,
            timeout=2.0,
        )
        response.raise_for_status()
    except Exception:
        # AgentTrace must never break the user's agent; keep the data locally.
        _persist_local_span(
            span_id=span_id,
            trace_id=trace_id,
            parent_span_id=parent_span_id,
            name=name,
            kind=kind,
            started_at=started_at,
            ended_at=ended_at,
            duration_ms=duration_ms,
            status=status,
            error_type=error_type,
            error_message=error_message,
            db_path=db_path,
        )