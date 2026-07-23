from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Define the interface required by all LLM providers."""

    @abstractmethod
    def classify_intent(self, message: str) -> str:
        """Classify the intent of a support request."""

        raise NotImplementedError

    @abstractmethod
    def generate_response(
        self,
        message: str,
        context: str,
        decision: str,
    ) -> str:
        """Generate a user-facing response grounded in retrieved context."""

        raise NotImplementedError


class RuleBasedLLMProvider(LLMProvider):
    """Provide deterministic local behaviour before a real LLM is connected."""

    def classify_intent(self, message: str) -> str:
        """Classify support intent with lightweight keyword rules."""

        normalized_message = message.lower()

        damaged_item_keywords = {
            "damaged",
            "broken",
            "defective",
            "missing parts",
            "arrived broken",
        }

        cancellation_keywords = {
            "cancel",
            "cancellation",
            "stop my order",
            "cancel my order",
            "do not ship",
        }

        late_delivery_keywords = {
            "delivery is late",
            "order is late",
            "package is late",
            "delayed",
            "overdue",
            "not arrived",
            "has not arrived",
            "still not arrived",
            "stuck in transit",
            "no tracking update",
            "tracking has not updated",
            "sitting with the courier",
            "has been sitting with the courier",
            "not moved",
            "no movement",
            "courier for several days",
        }

        shipping_keywords = {
            "shipping time",
            "delivery time",
            "estimated delivery",
            "when will it arrive",
            "when will my package arrive",
            "how long does shipping take",
            "shipping information",
            "delivery information",
        }

        refund_keywords = {
            "refund",
            "return",
            "money back",
            "reimburse",
        }

        order_status_keywords = {
            "where is my order",
            "order status",
            "tracking",
            "shipped",
            "delivered",
        }

        if any(
            keyword in normalized_message
            for keyword in damaged_item_keywords
        ):
            return "damaged_item_request"

        if any(
            keyword in normalized_message
            for keyword in cancellation_keywords
        ):
            return "cancellation_request"

        if any(
            keyword in normalized_message
            for keyword in late_delivery_keywords
        ):
            return "late_delivery_request"

        if any(
            keyword in normalized_message
            for keyword in shipping_keywords
        ):
            return "shipping_request"

        if any(
            keyword in normalized_message
            for keyword in refund_keywords
        ):
            return "refund_request"

        if any(
            keyword in normalized_message
            for keyword in order_status_keywords
        ):
            return "order_status"

        return "general_support"

    def generate_response(
        self,
        message: str,
        context: str,
        decision: str,
    ) -> str:
        """Generate a deterministic user-facing support response."""

        if decision == "approve_refund":
            return (
                "Your order appears eligible for a refund based on the "
                "retrieved policy and verified order details."
            )

        if decision == "approve_cancellation":
            return (
                "Your order appears eligible for cancellation based on "
                "its current fulfilment status."
            )

        if decision == "cancellation_not_available":
            return (
                "This order can no longer be cancelled automatically "
                "because fulfilment has already progressed."
            )

        if decision == "request_damage_evidence":
            return (
                "Please provide a description of the damage and photographic "
                "evidence when available so the request can be reviewed."
            )

        if decision == "shipping_information_provided":
            return context

        if decision == "delivery_in_progress":
            return (
                "Your order is still within the normal delivery process. "
                "Please continue monitoring the tracking information."
            )

        if decision == "delivery_delayed":
            return (
                "Your delivery appears to be delayed and may require "
                "additional support review."
            )

        if decision == "order_status_found":
            return context

        if decision == "escalate_to_human":
            return (
                "This request requires review by a human support agent."
            )

        if decision == "missing_order_id":
            return (
                "Please provide the order ID so I can check the request."
            )

        if decision == "order_not_found":
            return (
                "I could not find an order matching the provided order ID."
            )

        return "The request could not be completed automatically."