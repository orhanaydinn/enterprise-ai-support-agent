from typing import Any, Literal

from pydantic import BaseModel, Field


class ToolExecutionResult(BaseModel):
    """Represent the result of a controlled support-tool execution."""

    tool_name: str = Field(
        min_length=1,
        max_length=100,
    )

    status: Literal[
        "completed",
        "skipped",
        "failed",
    ]

    executed: bool

    reference_id: str | None = None

    message: str = Field(
        min_length=1,
        max_length=500,
    )

    data: dict[str, Any] = Field(
        default_factory=dict,
    )