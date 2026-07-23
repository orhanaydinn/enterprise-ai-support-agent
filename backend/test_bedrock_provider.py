from app.services.bedrock_llm_service import BedrockLLMProvider


def test_bedrock_provider() -> None:
    """Test customer-facing response generation through Amazon Bedrock."""

    provider = BedrockLLMProvider()

    response = provider.generate_response(
        message="Can I cancel my order?",
        context=(
            "The order is still processing and appears eligible "
            "for cancellation."
        ),
        decision="approve_cancellation",
    )

    print(response)


if __name__ == "__main__":
    test_bedrock_provider()