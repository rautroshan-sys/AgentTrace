import functools
import inspect
import uuid
from contextvars import ContextVar, Token
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

from agenttrace.models.trace import SpanStatus


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


def set_current_span(span: SpanContext | None | Token):
    if isinstance(span, Token):
        _current_span.reset(span)
        return None
    return _current_span.set(span)


def trace_agent(name: str | None = None):
    def decorator(func: Callable[..., Any]):
        agent_name = name or func.__name__

        if inspect.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                parent = get_current_span()
                span = SpanContext(
                    span_id=new_id("spn"),
                    trace_id=parent.trace_id if parent else new_id("trc"),
                    parent_span_id=parent.span_id if parent else None,
                    name=agent_name,
                    kind="agent",
                    started_at=now(),
                )
                token = set_current_span(span)
                started = datetime.now(timezone.utc)
                status = SpanStatus.OK
                error_type = None
                error_message = None
                try:
                    return await func(*args, **kwargs)
                except Exception as error:
                    status = SpanStatus.ERROR
                    error_type = type(error).__name__
                    error_message = str(error)
                    raise
                finally:
                    from agenttrace.sdk.exporter import export_span

                    ended = datetime.now(timezone.utc)
                    export_span(
                        span_id=span.span_id,
                        trace_id=span.trace_id,
                        parent_span_id=span.parent_span_id,
                        name=span.name,
                        kind=span.kind,
                        started_at=span.started_at,
                        ended_at=ended,
                        duration_ms=int((ended - started).total_seconds() * 1000),
                        status=status,
                        error_type=error_type,
                        error_message=error_message,
                    )
                    set_current_span(token)

            return async_wrapper

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            parent = get_current_span()
            span = SpanContext(
                span_id=new_id("spn"),
                trace_id=parent.trace_id if parent else new_id("trc"),
                parent_span_id=parent.span_id if parent else None,
                name=agent_name,
                kind="agent",
                started_at=now(),
            )
            token = set_current_span(span)
            started = datetime.now(timezone.utc)
            status = SpanStatus.OK
            error_type = None
            error_message = None
            try:
                return func(*args, **kwargs)
            except Exception as error:
                status = SpanStatus.ERROR
                error_type = type(error).__name__
                error_message = str(error)
                raise
            finally:
                from agenttrace.sdk.exporter import export_span

                ended = datetime.now(timezone.utc)
                export_span(
                    span_id=span.span_id,
                    trace_id=span.trace_id,
                    parent_span_id=span.parent_span_id,
                    name=span.name,
                    kind=span.kind,
                    started_at=span.started_at,
                    ended_at=ended,
                    duration_ms=int((ended - started).total_seconds() * 1000),
                    status=status,
                    error_type=error_type,
                    error_message=error_message,
                )
                set_current_span(token)

        return sync_wrapper

    return decorator