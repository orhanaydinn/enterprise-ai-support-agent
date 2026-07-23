import os
from datetime import UTC, datetime
from decimal import Decimal
from functools import lru_cache
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.models.responses import SupportResponse


SUPPORT_REQUESTS_TABLE = os.getenv("SUPPORT_REQUESTS_TABLE")


@lru_cache(maxsize=1)
def get_support_requests_table():
    """Create and cache the configured DynamoDB table resource."""

    if not SUPPORT_REQUESTS_TABLE:
        return None

    dynamodb = boto3.resource("dynamodb")

    return dynamodb.Table(SUPPORT_REQUESTS_TABLE)


def convert_for_dynamodb(value: Any) -> Any:
    """Convert Python values into DynamoDB-compatible values."""

    if isinstance(value, float):
        return Decimal(str(value))

    if isinstance(value, dict):
        return {
            key: convert_for_dynamodb(item)
            for key, item in value.items()
        }

    if isinstance(value, list):
        return [
            convert_for_dynamodb(item)
            for item in value
        ]

    return value


def store_support_response(
    response: SupportResponse,
) -> bool:
    """Persist the final support-agent response in DynamoDB."""

    table = get_support_requests_table()

    if table is None:
        return False

    tool_result = response.tool_result

    item = {
        "request_id": response.request_id,
        "record_type": "support_request",
        "created_at": datetime.now(UTC).isoformat(),
        "intent": response.intent,
        "message": response.message,
        "assistant_response": response.assistant_response,
        "order_id": response.order_id or "",
        "customer_id": response.customer_id or "",
        "status": response.status,
        "reason": response.reason,
        "eligible": response.eligible,
        "latency_ms": response.latency_ms,
        "tool_name": tool_result.tool_name,
        "tool_status": tool_result.status,
        "tool_executed": tool_result.executed,
        "ticket_id": tool_result.reference_id or "",
        "ticket_type": tool_result.data.get(
            "ticket_type",
            "",
        ),
        "persisted": True,
        "simulation": tool_result.data.get(
            "simulation",
            False,
        ),
        "citation_sources": [
            citation.source
            for citation in response.citations
        ],
        "trace_steps": [
            {
                "step": trace_step.step,
                "status": trace_step.status,
            }
            for trace_step in response.trace
        ],
    }

    table.put_item(
        Item=convert_for_dynamodb(item),
    )

    return True


def safely_store_support_response(
    response: SupportResponse,
) -> bool:
    """Persist a response without breaking the API when storage fails."""

    try:
        return store_support_response(response)

    except (BotoCoreError, ClientError, ValueError, TypeError):
        return False