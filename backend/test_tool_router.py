from app.agent.tool_router import route_support_tool


def run_router_tests() -> None:
    """Test supported and skipped tool-routing scenarios."""

    test_cases = [
        {
            "decision": "delivery_delayed",
            "request_id": "req_router_001",
            "customer_id": "CUS-1002",
            "order_id": "ORD-1002",
            "reason": "Tracking has not updated for several days.",
        },
        {
            "decision": "approve_refund",
            "request_id": "req_router_002",
            "customer_id": "CUS-1001",
            "order_id": "ORD-1001",
            "reason": "The delivered order appears refund eligible.",
        },
        {
            "decision": "approve_cancellation",
            "request_id": "req_router_003",
            "customer_id": "CUS-1004",
            "order_id": "ORD-1004",
            "reason": "The order has not yet entered shipment.",
        },
        {
            "decision": "request_damage_evidence",
            "request_id": "req_router_004",
            "customer_id": "CUS-1001",
            "order_id": "ORD-1001",
            "reason": "Damage evidence is required for review.",
        },
        {
            "decision": "escalate_to_human",
            "request_id": "req_router_005",
            "customer_id": "CUS-9999",
            "order_id": "ORD-1001",
            "reason": "The customer identity could not be verified.",
        },
        {
            "decision": "order_status_found",
            "request_id": "req_router_006",
            "customer_id": "CUS-1002",
            "order_id": "ORD-1002",
            "reason": "The current order status was returned.",
        },
    ]

    for test_case in test_cases:
        result = route_support_tool(**test_case)

        print("=" * 70)
        print(f"Decision: {test_case['decision']}")
        print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    run_router_tests()