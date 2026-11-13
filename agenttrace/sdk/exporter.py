import httpx

from agenttrace.sdk.context import now

API_URL = "http://127.0.0.1:8000"


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
        # AgentTrace must never break the user's agent.
        pass