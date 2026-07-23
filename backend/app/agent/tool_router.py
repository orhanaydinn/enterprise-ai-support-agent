from app.models.tools import ToolExecutionResult
from app.tools.ticket_tool import create_support_ticket


DECISION_TICKET_TYPE_MAP = {
    "escalate_to_human": "general_support",
    "delivery_delayed": "delivery_review",
    "approve_refund": "refund_review",
    "approve_cancellation": "cancellation_review",
    "request_damage_evidence": "damage_review",
}


def _build_skipped_result(
    *,
    decision: str,
    request_id: str,
) -> ToolExecutionResult:
    """Build a result for decisions that require no tool execution."""

    return ToolExecutionResult(
        tool_name="none",
        status="skipped",
        executed=False,
        message=(
            f"No simulated tool execution is required for "
            f"decision: {decision}."
        ),
        data={
            "decision": decision,
            "request_id": request_id,
            "simulation": True,
        },
    )


def route_support_tool(
    *,
    decision: str,
    request_id: str,
    customer_id: str | None,
    order_id: str | None,
    reason: str,
) -> ToolExecutionResult:
    """Route a validated decision to an allowed simulated support tool."""

    ticket_type = DECISION_TICKET_TYPE_MAP.get(decision)

    if ticket_type is None:
        return _build_skipped_result(
            decision=decision,
            request_id=request_id,
        )

    return create_support_ticket(
        ticket_type=ticket_type,
        request_id=request_id,
        customer_id=customer_id,
        order_id=order_id,
        reason=reason,
    )