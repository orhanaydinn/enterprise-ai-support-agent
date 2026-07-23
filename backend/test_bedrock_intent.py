from app.services.bedrock_llm_service import BedrockLLMProvider


def test_intent_classification() -> None:
    """Test structured intent classification through Amazon Bedrock."""

    provider = BedrockLLMProvider()

    test_messages = [
        "The parcel has not moved for several days.",
        "How long does standard shipping usually take?",
        "I want to cancel my order before it leaves the warehouse.",
        "The product arrived broken.",
        "Can you tell me the current status of my order?",
    ]

    for message in test_messages:
        result = provider.classify_intent(message)

        print("-" * 70)
        print(f"Message: {message}")
        print(f"Intent: {result.intent.value}")
        print(f"Confidence: {result.confidence}")
        print(f"Reason: {result.reason}")


if __name__ == "__main__":
    test_intent_classification()