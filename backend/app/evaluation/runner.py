from dataclasses import asdict
from statistics import mean

from app.agent.workflows import process_support_request
from app.evaluation.cases import EVALUATION_CASES, EvaluationCase
from app.models.requests import SupportRequest


def _contains_forbidden_phrase(
    response_text: str,
    forbidden_phrases: tuple[str, ...],
) -> tuple[bool, str | None]:
    """Check whether a response contains a forbidden phrase."""

    normalized_response = response_text.lower()

    for phrase in forbidden_phrases:
        if phrase.lower() in normalized_response:
            return True, phrase

    return False, None


def _extract_response_source(trace: list) -> str:
    """Extract the response source from the execution trace."""

    for step in trace:
        if step.step != "response_generation":
            continue

        detail = step.detail.lower()

        if "response source: amazon_bedrock" in detail:
            return "amazon_bedrock"

        if "response source: deterministic_safety_fallback" in detail:
            return "deterministic_safety_fallback"

        if "response source: deterministic_provider_fallback" in detail:
            return "deterministic_provider_fallback"

    return "unknown"


def _extract_intent_provider(trace: list) -> str:
    """Extract the intent-classification provider from the trace."""

    for step in trace:
        if step.step != "intent_classification":
            continue

        detail = step.detail.lower()

        if "deterministic fallback intent" in detail:
            return "deterministic_fallback"

        if "deterministic intent classifier was used" in detail:
            return "deterministic_fallback"

        if "using amazon bedrock" in detail:
            return "amazon_bedrock"

    return "unknown"


def evaluate_case(
    evaluation_case: EvaluationCase,
) -> dict:
    """Run one end-to-end evaluation case."""

    request = SupportRequest(
        message=evaluation_case.message,
        order_id=evaluation_case.order_id,
        customer_id=evaluation_case.customer_id,
    )

    response = process_support_request(request)

    forbidden_phrase_found, matched_phrase = (
        _contains_forbidden_phrase(
            response_text=response.assistant_response,
            forbidden_phrases=(
                evaluation_case.forbidden_response_phrases
            ),
        )
    )

    actual_ticket_type = response.tool_result.data.get(
        "ticket_type",
    )

    intent_passed = (
        response.intent == evaluation_case.expected_intent
    )

    status_passed = (
        response.status == evaluation_case.expected_status
    )

    eligible_passed = (
        response.eligible == evaluation_case.expected_eligible
    )

    safety_passed = not forbidden_phrase_found

    tool_name_passed = (
        response.tool_result.tool_name
        == evaluation_case.expected_tool_name
    )

    tool_status_passed = (
        response.tool_result.status
        == evaluation_case.expected_tool_status
    )

    tool_executed_passed = (
        response.tool_result.executed
        == evaluation_case.expected_tool_executed
    )

    ticket_type_passed = (
        actual_ticket_type
        == evaluation_case.expected_ticket_type
    )

    tool_passed = all(
        (
            tool_name_passed,
            tool_status_passed,
            tool_executed_passed,
            ticket_type_passed,
        )
    )

    case_passed = all(
        (
            intent_passed,
            status_passed,
            eligible_passed,
            safety_passed,
            tool_passed,
        )
    )

    return {
        "case_id": evaluation_case.case_id,
        "message": evaluation_case.message,
        "expected": {
            "intent": evaluation_case.expected_intent,
            "status": evaluation_case.expected_status,
            "eligible": evaluation_case.expected_eligible,
            "tool_name": evaluation_case.expected_tool_name,
            "tool_status": evaluation_case.expected_tool_status,
            "tool_executed": (
                evaluation_case.expected_tool_executed
            ),
            "ticket_type": evaluation_case.expected_ticket_type,
        },
        "actual": {
            "intent": response.intent,
            "status": response.status,
            "eligible": response.eligible,
            "assistant_response": response.assistant_response,
            "tool_name": response.tool_result.tool_name,
            "tool_status": response.tool_result.status,
            "tool_executed": response.tool_result.executed,
            "tool_reference_id": (
                response.tool_result.reference_id
            ),
            "ticket_type": actual_ticket_type,
        },
        "checks": {
            "intent_passed": intent_passed,
            "status_passed": status_passed,
            "eligible_passed": eligible_passed,
            "safety_passed": safety_passed,
            "tool_name_passed": tool_name_passed,
            "tool_status_passed": tool_status_passed,
            "tool_executed_passed": tool_executed_passed,
            "ticket_type_passed": ticket_type_passed,
            "tool_passed": tool_passed,
            "matched_forbidden_phrase": matched_phrase,
        },
        "providers": {
            "intent_provider": _extract_intent_provider(
                response.trace,
            ),
            "response_source": _extract_response_source(
                response.trace,
            ),
        },
        "latency_ms": response.latency_ms,
        "passed": case_passed,
    }


def run_evaluation() -> dict:
    """Run the complete support-agent evaluation suite."""

    results = [
        evaluate_case(evaluation_case)
        for evaluation_case in EVALUATION_CASES
    ]

    total_cases = len(results)

    passed_cases = sum(
        1
        for result in results
        if result["passed"]
    )

    intent_passes = sum(
        1
        for result in results
        if result["checks"]["intent_passed"]
    )

    status_passes = sum(
        1
        for result in results
        if result["checks"]["status_passed"]
    )

    eligible_passes = sum(
        1
        for result in results
        if result["checks"]["eligible_passed"]
    )

    safety_passes = sum(
        1
        for result in results
        if result["checks"]["safety_passed"]
    )

    tool_passes = sum(
        1
        for result in results
        if result["checks"]["tool_passed"]
    )

    latencies = [
        result["latency_ms"]
        for result in results
    ]

    response_source_counts: dict[str, int] = {}
    intent_provider_counts: dict[str, int] = {}
    tool_name_counts: dict[str, int] = {}
    ticket_type_counts: dict[str, int] = {}

    for result in results:
        response_source = result["providers"]["response_source"]
        intent_provider = result["providers"]["intent_provider"]
        tool_name = result["actual"]["tool_name"]
        ticket_type = result["actual"]["ticket_type"]

        response_source_counts[response_source] = (
            response_source_counts.get(response_source, 0) + 1
        )

        intent_provider_counts[intent_provider] = (
            intent_provider_counts.get(intent_provider, 0) + 1
        )

        tool_name_counts[tool_name] = (
            tool_name_counts.get(tool_name, 0) + 1
        )

        if ticket_type is not None:
            ticket_type_counts[ticket_type] = (
                ticket_type_counts.get(ticket_type, 0) + 1
            )

    failed_cases = [
        result
        for result in results
        if not result["passed"]
    ]

    return {
        "summary": {
            "total_cases": total_cases,
            "passed_cases": passed_cases,
            "failed_cases": total_cases - passed_cases,
            "overall_pass_rate": round(
                passed_cases / total_cases,
                4,
            ),
            "intent_accuracy": round(
                intent_passes / total_cases,
                4,
            ),
            "status_accuracy": round(
                status_passes / total_cases,
                4,
            ),
            "eligible_accuracy": round(
                eligible_passes / total_cases,
                4,
            ),
            "safety_pass_rate": round(
                safety_passes / total_cases,
                4,
            ),
            "tool_accuracy": round(
                tool_passes / total_cases,
                4,
            ),
            "average_latency_ms": round(
                mean(latencies),
                2,
            ),
            "minimum_latency_ms": round(
                min(latencies),
                2,
            ),
            "maximum_latency_ms": round(
                max(latencies),
                2,
            ),
            "response_source_counts": response_source_counts,
            "intent_provider_counts": intent_provider_counts,
            "tool_name_counts": tool_name_counts,
            "ticket_type_counts": ticket_type_counts,
        },
        "failed_cases": failed_cases,
        "results": results,
    }


def serialize_evaluation_cases() -> list[dict]:
    """Return the configured evaluation cases as dictionaries."""

    return [
        asdict(evaluation_case)
        for evaluation_case in EVALUATION_CASES
    ]