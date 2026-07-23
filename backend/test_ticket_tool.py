from app.tools.ticket_tool import create_support_ticket


def test_ticket_tool() -> None:
    """Test simulated support-ticket creation."""

    result = create_support_ticket(
        ticket_type="delivery_review",
        request_id="req_test_001",
        customer_id="CUS-1002",
        order_id="ORD-1002",
        reason="Tracking has not updated for more than three days.",
    )

    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    test_ticket_tool()