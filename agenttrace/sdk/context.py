import uuid
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime, timezone


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:24]}"


def now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class SpanContext:
    span_id: str
    trace_id: str
    parent_span_id: str | None
    name: str
    kind: str
    started_at: datetime
    attributes: dict = field(default_factory=dict)


_current_span: ContextVar[SpanContext | None] = ContextVar(
    "agenttrace_current_span",
    default=None,
)


def get_current_span() -> SpanContext | None:
    return _current_span.get()


def set_current_span(span: SpanContext | None) -> None:
    _current_span.set(span)