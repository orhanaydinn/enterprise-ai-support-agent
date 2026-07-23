def validate_customer_identity(
    order: dict,
    customer_id: str | None,
) -> dict:
    """Validate that the request customer matches the order owner."""

    if customer_id is None:
        return {
            "valid": False,
            "reason": "A customer ID is required to verify order ownership.",
        }

    if customer_id.strip().upper() != order["customer_id"]:
        return {
            "valid": False,
            "reason": "The customer ID does not match the order record.",
        }

    return {
        "valid": True,
        "reason": "The customer identity matches the order record.",
    }

def evaluate_refund_eligibility(order: dict) -> dict:
    """Evaluate whether an order is eligible for an automatic refund."""

    if order["status"] != "delivered":
        return {
            "eligible": False,
            "decision": "escalate_to_human",
            "reason": (
                "The order is not delivered, so it is not eligible "
                "for an automatic refund."
            ),
        }

    delivered_days_ago = order.get("delivered_days_ago")

    if delivered_days_ago is None:
        return {
            "eligible": False,
            "decision": "escalate_to_human",
            "reason": "The delivery date cannot be verified.",
        }

    if delivered_days_ago > 14:
        return {
            "eligible": False,
            "decision": "escalate_to_human",
            "reason": (
                "The order was delivered more than 14 days ago."
            ),
        }

    return {
        "eligible": True,
        "decision": "approve_refund",
        "reason": (
            "The order was delivered within the 14-day refund window."
        ),
    }


def evaluate_damaged_item_request(order: dict) -> dict:
    """Evaluate whether a damaged-item request can proceed automatically."""

    if order["status"] != "delivered":
        return {
            "eligible": False,
            "decision": "escalate_to_human",
            "reason": (
                "The order is not marked as delivered, so the damaged-item "
                "request requires human review."
            ),
        }

    delivered_days_ago = order.get("delivered_days_ago")

    if delivered_days_ago is None:
        return {
            "eligible": False,
            "decision": "escalate_to_human",
            "reason": "The delivery date cannot be verified.",
        }

    if delivered_days_ago > 7:
        return {
            "eligible": False,
            "decision": "escalate_to_human",
            "reason": (
                "The damage was reported more than 7 days after delivery."
            ),
        }

    return {
        "eligible": False,
        "decision": "request_damage_evidence",
        "reason": (
            "The order was delivered within the 7-day damaged-item "
            "reporting window, but damage evidence is required."
        ),
    }

def evaluate_cancellation_request(order: dict) -> dict:
    """Evaluate whether an order can be cancelled automatically."""

    order_status = order.get("status")

    if order_status == "processing":
        return {
            "eligible": True,
            "decision": "approve_cancellation",
            "reason": (
                "The order is still processing and appears eligible "
                "for cancellation."
            ),
        }

    if order_status == "shipped":
        return {
            "eligible": False,
            "decision": "cancellation_not_available",
            "reason": (
                "The order has already been shipped and cannot be "
                "cancelled automatically."
            ),
        }

    if order_status == "delivered":
        return {
            "eligible": False,
            "decision": "cancellation_not_available",
            "reason": (
                "The order has already been delivered and cannot be "
                "cancelled."
            ),
        }

    if order_status == "cancelled":
        return {
            "eligible": False,
            "decision": "cancellation_not_available",
            "reason": "The order has already been cancelled.",
        }

    if order_status == "refunded":
        return {
            "eligible": False,
            "decision": "cancellation_not_available",
            "reason": (
                "The order has already been refunded and cannot be "
                "cancelled."
            ),
        }

    return {
        "eligible": False,
        "decision": "escalate_to_human",
        "reason": (
            "The order fulfilment status could not be evaluated, "
            "so human review is required."
        ),
    }

def evaluate_shipping_request(order: dict) -> dict:
    """Provide shipping guidance based on the current order status."""

    order_status = order.get("status")

    if order_status == "processing":
        return {
            "eligible": True,
            "decision": "shipping_information_provided",
            "reason": (
                "The order is still processing. Orders are normally "
                "processed within 1 to 2 business days."
            ),
        }

    if order_status == "shipped":
        return {
            "eligible": True,
            "decision": "shipping_information_provided",
            "reason": (
                "The order has been shipped. Standard delivery normally "
                "takes 3 to 5 business days after shipment."
            ),
        }

    if order_status == "delivered":
        return {
            "eligible": True,
            "decision": "shipping_information_provided",
            "reason": "The order has already been delivered.",
        }

    if order_status == "cancelled":
        return {
            "eligible": False,
            "decision": "shipping_information_provided",
            "reason": (
                "The order was cancelled and will not enter the "
                "shipping process."
            ),
        }

    return {
        "eligible": False,
        "decision": "escalate_to_human",
        "reason": (
            "The current shipping status could not be evaluated, "
            "so human review is required."
        ),
    }


def evaluate_late_delivery_request(order: dict) -> dict:
    """Evaluate whether a delivery delay requires human review."""

    order_status = order.get("status")

    if order_status == "processing":
        return {
            "eligible": False,
            "decision": "delivery_in_progress",
            "reason": (
                "The order is still processing and has not yet entered "
                "the delivery stage."
            ),
        }

    if order_status == "shipped":
        return {
            "eligible": False,
            "decision": "delivery_delayed",
            "reason": (
                "The order is still marked as shipped. A delay may require "
                "tracking review if the estimated delivery date has passed."
            ),
        }

    if order_status == "delivered":
        return {
            "eligible": False,
            "decision": "escalate_to_human",
            "reason": (
                "The order is marked as delivered, but the customer reports "
                "that it has not arrived."
            ),
        }

    if order_status == "cancelled":
        return {
            "eligible": False,
            "decision": "escalate_to_human",
            "reason": (
                "The order was cancelled and should not be in transit."
            ),
        }

    return {
        "eligible": False,
        "decision": "escalate_to_human",
        "reason": (
            "The delivery status could not be evaluated, "
            "so human review is required."
        ),
    }