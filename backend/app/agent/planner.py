from app.services.llm_service import RuleBasedLLMProvider


llm_provider = RuleBasedLLMProvider()


def classify_intent(message: str) -> str:
    """Classify a support request through the configured LLM provider."""

    return llm_provider.classify_intent(message)