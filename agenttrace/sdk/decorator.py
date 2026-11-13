import functools
import inspect
from datetime import datetime, timezone

from agenttrace.models.trace import SpanKind, SpanStatus
from agenttrace.sdk.context import (
    SpanContext,
    get_current_span,
    new_id,
    now,
    set_current_span,
)
from agenttrace.sdk.exporter import export_span


def observe(kind: SpanKind, name: str | None = None):
    def decorator(func):
        span_name = name or func.__name__

        if inspect.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                parent = get_current_span()
                span = SpanContext(
                    span_id=new_id("spn"),
                    trace_id=parent.trace_id if parent else new_id("trc"),
                    parent_span_id=parent.span_id if parent else None,
                    name=span_name,
                    kind=kind.value,
                    started_at=now(),
                )

                token = set_current_span(span)
                started = datetime.now(timezone.utc)

                try:
                    result = await func(*args, **kwargs)
                    status = SpanStatus.OK
                    error_type = None
                    error_message = None
                    return result
                except Exception as error:
                    status = SpanStatus.ERROR
                    error_type = type(error).__name__
                    error_message = str(error)
                    raise
                finally:
                    ended = datetime.now(timezone.utc)
                    duration_ms = int((ended - started).total_seconds() * 1000)

                    export_span(
                        span_id=span.span_id,
                        trace_id=span.trace_id,
                        parent_span_id=span.parent_span_id,
                        name=span.name,
                        kind=span.kind,
                        started_at=span.started_at,
                        ended_at=ended,
                        duration_ms=duration_ms,
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
                name=span_name,
                kind=kind.value,
                started_at=now(),
            )

            token = set_current_span(span)
            started = datetime.now(timezone.utc)

            try:
                result = func(*args, **kwargs)
                status = SpanStatus.OK
                error_type = None
                error_message = None
                return result
            except Exception as error:
                status = SpanStatus.ERROR
                error_type = type(error).__name__
                error_message = str(error)
                raise
            finally:
                ended = datetime.now(timezone.utc)
                duration_ms = int((ended - started).total_seconds() * 1000)

                export_span(
                    span_id=span.span_id,
                    trace_id=span.trace_id,
                    parent_span_id=span.parent_span_id,
                    name=span.name,
                    kind=span.kind,
                    started_at=span.started_at,
                    ended_at=ended,
                    duration_ms=duration_ms,
                    status=status,
                    error_type=error_type,
                    error_message=error_message,
                )

                set_current_span(token)

        return sync_wrapper

    return decorator