from typing import Literal

from pydantic import BaseModel, Field

from app.models.tools import ToolExecutionResult


class AgentTraceStep(BaseModel):
    """Represent one observable step in the agent workflow."""

    step: str = Field(
        min_length=1,
        max_length=100,
    )

    status: Literal[
        "completed",
        "skipped",
        "failed",
    ]

    detail: str = Field(
        min_length=1,
        max_length=1000,
    )


class Citation(BaseModel):
    """Represent one policy citation returned by semantic retrieval."""

    source: str = Field(
        min_length=1,
        max_length=255,
    )

    reference: str = Field(
        min_length=1,
        max_length=255,
    )

    excerpt: str = Field(
        min_length=1,
        max_length=2000,
    )


class SupportResponse(BaseModel):
    """Represent the complete enterprise support-agent response."""

    request_id: str = Field(
        min_length=1,
        max_length=100,
    )

    intent: str = Field(
        min_length=1,
        max_length=100,
    )

    message: str = Field(
        min_length=1,
        max_length=5000,
    )

    assistant_response: str = Field(
        min_length=1,
        max_length=5000,
    )

    order_id: str | None = None
    customer_id: str | None = None

    status: str = Field(
        min_length=1,
        max_length=100,
    )

    reason: str = Field(
        min_length=1,
        max_length=2000,
    )

    eligible: bool

    latency_ms: float = Field(
        ge=0.0,
    )

    tool_result: ToolExecutionResult

    citations: list[Citation] = Field(
        default_factory=list,
    )

    trace: list[AgentTraceStep] = Field(
        default_factory=list,
    )