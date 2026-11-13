from datetime import datetime
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class SpanKind(str, Enum):
    AGENT = "agent"
    LLM = "llm"
    RETRIEVER = "retriever"
    TOOL = "tool"
    EVALUATOR = "evaluator"


class SpanStatus(str, Enum):
    OK = "ok"
    ERROR = "error"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class SpanCreate(BaseModel):
    span_id: str
    trace_id: str
    parent_span_id: str | None = None
    name: str
    kind: SpanKind
    started_at: datetime
    ended_at: datetime | None = None
    duration_ms: int | None = None
    status: SpanStatus = SpanStatus.OK
    attributes: dict[str, Any] = Field(default_factory=dict)
    input_payload: dict[str, Any] | None = None
    output_payload: dict[str, Any] | None = None
    error_type: str | None = None
    error_message: str | None = None


class TraceCreate(BaseModel):
    trace_id: str
    root_span_id: str
    agent_name: str
    agent_version: str
    started_at: datetime
    ended_at: datetime | None = None
    status: SpanStatus = SpanStatus.OK
    metadata: dict[str, Any] = Field(default_factory=dict)
    spans: list[SpanCreate] = Field(default_factory=list)