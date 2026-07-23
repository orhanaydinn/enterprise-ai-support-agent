from pydantic import BaseModel, Field
from pydantic import BaseModel

class SupportRequest(BaseModel):
    """Represent a customer support request sent to the AI agent."""

    message: str = Field(
        ...,
        min_length=5,
        max_length=2000,
        description="Customer support request written in natural language.",
    )

    order_id: str | None = Field(
        default=None,
        max_length=50,
        description="Optional order identifier.",
    )

    customer_id: str | None = Field(
        default=None,
        max_length=50,
        description="Optional customer identifier.",
    )

class SupportResponse(BaseModel):
    """Represent the initial response returned by the support API."""

    message: str
    order_id: str | None
    customer_id: str | None
    status: str