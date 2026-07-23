from enum import Enum

from pydantic import BaseModel, Field


class SupportIntent(str, Enum):
    """Define the support intents accepted by the application."""

    REFUND_REQUEST = "refund_request"
    DAMAGED_ITEM_REQUEST = "damaged_item_request"
    CANCELLATION_REQUEST = "cancellation_request"
    SHIPPING_REQUEST = "shipping_request"
    LATE_DELIVERY_REQUEST = "late_delivery_request"
    ORDER_STATUS = "order_status"
    GENERAL_SUPPORT = "general_support"


class IntentClassification(BaseModel):
    """Represent a validated intent-classification result."""

    intent: SupportIntent

    confidence: float = Field(
        ge=0.0,
        le=1.0,
    )

    reason: str = Field(
        min_length=1,
        max_length=300,
    )