from datetime import datetime, timezone

import pytest

from agenttrace.db.database import initialize_database
from agenttrace.db.repository import get_trace, insert_trace
from agenttrace.models.trace import (
    SpanCreate,
    SpanKind,
    SpanStatus,
    TraceCreate,
)
from agenttrace.sdk import exporter
from agenttrace.sdk.context import SpanContext, get_current_span, set_current_span, trace_agent


def make_trace() -> TraceCreate:
    now = datetime.now(timezone.utc)

    agent_span = SpanCreate(
        span_id="spn_agent",
        trace_id="trc_001",
        parent_span_id=None,
        name="invoke_agent support-agent",
        kind=SpanKind.AGENT,
        started_at=now,
        ended_at=now,
        duration_ms=100,
        status=SpanStatus.OK,
    )

    llm_span = SpanCreate(
        span_id="spn_llm",
        trace_id="trc_001",
        parent_span_id="spn_agent",
        name="chat",
        kind=SpanKind.LLM,
        started_at=now,
        ended_at=now,
        duration_ms=50,
        status=SpanStatus.OK,
    )

    tool_span = SpanCreate(
        span_id="spn_tool",
        trace_id="trc_001",
        parent_span_id="spn_agent",
        name="get_order_status",
        kind=SpanKind.TOOL,
        started_at=now,
        ended_at=now,
        duration_ms=30,
        status=SpanStatus.ERROR,
        error_type="timeout",
        error_message="order service unavailable",
    )

    return TraceCreate(
        trace_id="trc_001",
        root_span_id="spn_agent",
        agent_name="support-agent",
        agent_version="v0.1.0",
        started_at=now,
        ended_at=now,
        status=SpanStatus.ERROR,
        metadata={"user_id": "user_123"},
        spans=[agent_span, llm_span, tool_span],
    )


def test_insert_and_get_trace(tmp_path):
    db_path = tmp_path / "test.db"
    initialize_database(db_path)

    trace = make_trace()
    inserted_trace_id = insert_trace(trace, db_path=str(db_path))

    assert inserted_trace_id == "trc_001"

    saved_trace = get_trace("trc_001", db_path=str(db_path))

    assert saved_trace is not None
    assert saved_trace["agent_name"] == "support-agent"
    assert saved_trace["status"] == "error"
    assert len(saved_trace["spans"]) == 3

    span_ids = {span["span_id"] for span in saved_trace["spans"]}
    assert span_ids == {"spn_agent", "spn_llm", "spn_tool"}

    tool_span = next(
        span for span in saved_trace["spans"]
        if span["span_id"] == "spn_tool"
    )

    assert tool_span["parent_span_id"] == "spn_agent"
    assert tool_span["status"] == "error"
    assert tool_span["error_type"] == "timeout"


def test_trace_context_and_agent_decorator():
    span = SpanContext(
        span_id="spn_1",
        trace_id="trc_1",
        parent_span_id=None,
        name="agent-root",
        kind="agent",
        started_at=datetime.now(timezone.utc),
    )

    token = set_current_span(span)
    assert token is not None
    assert get_current_span() == span

    reset = set_current_span(None)
    assert reset is not None
    assert get_current_span() is None

    @trace_agent(name="support-agent")
    def get_response() -> str:
        return "ok"

    assert get_response() == "ok"


def test_export_span_falls_back_to_sqlite(monkeypatch, tmp_path):
    db_path = tmp_path / "fallback.db"
    initialize_database(db_path)

    def fail_http(*args, **kwargs):
        raise RuntimeError("offline")

    monkeypatch.setattr(exporter.httpx, "post", fail_http)

    exporter.export_span(
        span_id="spn_agent",
        trace_id="trc_001",
        parent_span_id=None,
        name="support-agent",
        kind="agent",
        started_at=datetime.now(timezone.utc),
        ended_at=datetime.now(timezone.utc),
        duration_ms=12,
        status=SpanStatus.OK,
        db_path=str(db_path),
    )

    saved_trace = get_trace("trc_001", db_path=str(db_path))
    assert saved_trace is not None
    assert saved_trace["root_span_id"] == "spn_agent"
    assert saved_trace["spans"][0]["parent_span_id"] is None


def test_trace_agent_marks_error_when_wrapped_function_raises(monkeypatch):
    calls = []

    def record_export(**kwargs):
        calls.append(kwargs)

    monkeypatch.setattr("agenttrace.sdk.exporter.export_span", record_export)

    @trace_agent(name="support-agent")
    def fail():
        raise TimeoutError("order service unavailable")

    with pytest.raises(TimeoutError):
        fail()

    assert calls
    assert calls[0]["status"] == SpanStatus.ERROR