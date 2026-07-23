import os
from datetime import UTC, datetime
from functools import lru_cache
from uuid import uuid4

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.models.tools import ToolExecutionResult


SUPPORTED_TICKET_TYPES = {
    "general_support",
    "identity_review",
    "refund_review",
    "cancellation_review",
    "damage_review",
    "delivery_review",
    "policy_review",
}

SUPPORT_REQUESTS_TABLE = os.getenv("SUPPORT_REQUESTS_TABLE")


def _generate_ticket_id() -> str:
    """Generate a unique support-ticket reference."""

    return f"TKT-{uuid4().hex[:10].upper()}"


def _utc_timestamp() -> str:
    """Return the current UTC timestamp in ISO 8601 format."""

    return datetime.now(UTC).isoformat()


@lru_cache(maxsize=1)
def _get_dynamodb_table():
    """Create and cache the configured DynamoDB table resource."""

    if not SUPPORT_REQUESTS_TABLE:
        return None

    dynamodb = boto3.resource("dynamodb")

    return dynamodb.Table(SUPPORT_REQUESTS_TABLE)


def _store_ticket(
    *,
    ticket_id: str,
    ticket_type: str,
    request_id: str,
    customer_id: str | None,
    order_id: str | None,
    reason: str,
) -> bool:
    """Persist a support ticket to DynamoDB when configured."""

    table = _get_dynamodb_table()

    if table is None:
        return False

    item = {
        "request_id": request_id,
        "record_type": "support_ticket",
        "ticket_id": ticket_id,
        "ticket_type": ticket_type,
        "customer_id": customer_id or "",
        "order_id": order_id or "",
        "reason": reason,
        "status": "open",
        "created_at": _utc_timestamp(),
        "simulation": False,
    }

    table.put_item(Item=item)

    return True


def create_support_ticket(
    *,
    ticket_type: str,
    request_id: str,
    customer_id: str | None,
    order_id: str | None,
    reason: str,
) -> ToolExecutionResult:
    """Create and optionally persist a support ticket for human review."""

    if ticket_type not in SUPPORTED_TICKET_TYPES:
        return ToolExecutionResult(
            tool_name="create_support_ticket",
            status="failed",
            executed=False,
            message=(
                f"Unsupported support-ticket type: {ticket_type}."
            ),
            data={
                "ticket_type": ticket_type,
                "request_id": request_id,
                "persisted": False,
            },
        )

    ticket_id = _generate_ticket_id()

    try:
        persisted = _store_ticket(
            ticket_id=ticket_id,
            ticket_type=ticket_type,
            request_id=request_id,
            customer_id=customer_id,
            order_id=order_id,
            reason=reason,
        )
    except (BotoCoreError, ClientError) as exc:
        return ToolExecutionResult(
            tool_name="create_support_ticket",
            status="failed",
            executed=False,
            reference_id=ticket_id,
            message="The support ticket could not be stored.",
            data={
                "ticket_id": ticket_id,
                "ticket_type": ticket_type,
                "request_id": request_id,
                "customer_id": customer_id,
                "order_id": order_id,
                "reason": reason,
                "persisted": False,
                "error": str(exc),
            },
        )

    return ToolExecutionResult(
        tool_name="create_support_ticket",
        status="completed",
        executed=True,
        reference_id=ticket_id,
        message=(
            "A support ticket was created and stored in DynamoDB."
            if persisted
            else "A simulated support ticket was created."
        ),
        data={
            "ticket_id": ticket_id,
            "ticket_type": ticket_type,
            "request_id": request_id,
            "customer_id": customer_id,
            "order_id": order_id,
            "reason": reason,
            "persisted": persisted,
            "simulation": not persisted,
        },
    )