from time import perf_counter

from app.agent.planner import classify_intent
from app.agent.tool_router import route_support_tool
from app.agent.validator import (
    evaluate_cancellation_request,
    evaluate_damaged_item_request,
    evaluate_late_delivery_request,
    evaluate_refund_eligibility,
    evaluate_shipping_request,
    validate_customer_identity,
)
from app.core.config import settings
from app.models.requests import SupportRequest
from app.models.responses import (
    AgentTraceStep,
    Citation,
    SupportResponse,
)
from app.models.tools import ToolExecutionResult
from app.services.bedrock_llm_service import BedrockLLMProvider
from app.services.llm_service import RuleBasedLLMProvider
from app.services.policy_service import retrieve_policy_context
from app.tools.order_tool import get_order_by_id
from app.utils.ids import generate_request_id
from app.services.request_store import safely_store_support_response

rule_based_provider = RuleBasedLLMProvider()
bedrock_provider = BedrockLLMProvider()


def calculate_latency_ms(start_time: float) -> float:
    """Calculate elapsed request processing time in milliseconds."""

    return round(
        (perf_counter() - start_time) * 1000,
        2,
    )


def build_citation_excerpt(
    content: str,
    max_length: int | None = None,
) -> str:
    """Build a readable citation excerpt without cutting words."""

    excerpt_length = (
        max_length
        if max_length is not None
        else settings.citation_excerpt_length
    )

    cleaned_content = " ".join(content.split())

    if len(cleaned_content) <= excerpt_length:
        return cleaned_content

    shortened_content = cleaned_content[:excerpt_length].rsplit(
        " ",
        1,
    )[0]

    if not shortened_content:
        shortened_content = cleaned_content[:excerpt_length]

    return f"{shortened_content}..."


def classify_support_intent(
    *,
    message: str,
    trace: list[AgentTraceStep],
) -> str:
    """Classify intent through Bedrock with a deterministic fallback."""

    try:
        classification = bedrock_provider.classify_intent(message)

        bedrock_intent = classification.intent.value
        confidence = classification.confidence

        if confidence >= settings.intent_confidence_threshold:
            trace.append(
                AgentTraceStep(
                    step="intent_classification",
                    status="completed",
                    detail=(
                        f"Classified request as {bedrock_intent} using "
                        "Amazon Bedrock. "
                        f"Confidence: {confidence:.2f}. "
                        f"Reason: {classification.reason}"
                    ),
                )
            )

            return bedrock_intent

        fallback_intent = classify_intent(message)

        trace.append(
            AgentTraceStep(
                step="intent_classification",
                status="completed",
                detail=(
                    "Amazon Bedrock returned a classification below the "
                    "configured confidence threshold of "
                    f"{settings.intent_confidence_threshold:.2f}. "
                    f"Bedrock intent: {bedrock_intent}. "
                    f"Confidence: {confidence:.2f}. "
                    f"Deterministic fallback intent: {fallback_intent}."
                ),
            )
        )

        return fallback_intent

    except RuntimeError as error:
        fallback_intent = classify_intent(message)

        trace.append(
            AgentTraceStep(
                step="intent_classification",
                status="completed",
                detail=(
                    "Amazon Bedrock intent classification was unavailable. "
                    "The deterministic intent classifier was used. "
                    f"Fallback intent: {fallback_intent}. "
                    f"Failure type: {type(error).__name__}."
                ),
            )
        )

        return fallback_intent


def generate_assistant_response(
    *,
    message: str,
    context: str,
    decision: str,
    trace: list[AgentTraceStep],
    response_description: str,
) -> str:
    """Generate a Bedrock response with deterministic fallbacks."""

    try:
        generation_result = bedrock_provider.generate_response_result(
            message=message,
            context=context,
            decision=decision,
        )

        if generation_result.source == "amazon_bedrock":
            detail = (
                f"{response_description} "
                "Provider: Amazon Bedrock. "
                f"Model: {bedrock_provider.model_id}. "
                "Response source: amazon_bedrock."
            )
        else:
            detail = (
                f"{response_description} "
                "Amazon Bedrock generated a response, but output "
                "validation rejected it. "
                "Response source: deterministic_safety_fallback. "
                f"Safety reason: {generation_result.safety_reason}. "
                f"Model: {bedrock_provider.model_id}."
            )

        trace.append(
            AgentTraceStep(
                step="response_generation",
                status="completed",
                detail=detail,
            )
        )

        return generation_result.text

    except RuntimeError as error:
        assistant_response = rule_based_provider.generate_response(
            message=message,
            context=context,
            decision=decision,
        )

        trace.append(
            AgentTraceStep(
                step="response_generation",
                status="completed",
                detail=(
                    f"{response_description} "
                    "Amazon Bedrock was unavailable. "
                    "Response source: deterministic_provider_fallback. "
                    f"Failure type: {type(error).__name__}."
                ),
            )
        )

        return assistant_response


def execute_support_tool(
    *,
    decision: str,
    request_id: str,
    customer_id: str | None,
    order_id: str | None,
    reason: str,
    trace: list[AgentTraceStep],
) -> ToolExecutionResult:
    """Route and execute an allowed simulated support tool."""

    tool_result = route_support_tool(
        decision=decision,
        request_id=request_id,
        customer_id=customer_id,
        order_id=order_id,
        reason=reason,
    )

    if tool_result.tool_name == "none":
        trace.append(
            AgentTraceStep(
                step="tool_routing",
                status="completed",
                detail=(
                    f"No support tool is mapped to decision: {decision}."
                ),
            )
        )

        trace.append(
            AgentTraceStep(
                step="tool_execution",
                status="skipped",
                detail=tool_result.message,
            )
        )

        return tool_result

    trace.append(
        AgentTraceStep(
            step="tool_routing",
            status="completed",
            detail=(
                f"Routed decision {decision} to simulated tool "
                f"{tool_result.tool_name}. "
                f"Ticket type: "
                f"{tool_result.data.get('ticket_type', 'unknown')}."
            ),
        )
    )

    if tool_result.status == "completed":
        trace.append(
            AgentTraceStep(
                step="tool_execution",
                status="completed",
                detail=(
                    f"Simulated tool {tool_result.tool_name} completed. "
                    f"Reference ID: {tool_result.reference_id}. "
                    "No real-world refund, cancellation, shipment, or "
                    "account action was executed."
                ),
            )
        )

        return tool_result

    trace.append(
        AgentTraceStep(
            step="tool_execution",
            status="failed",
            detail=(
                f"Simulated tool {tool_result.tool_name} failed. "
                f"Reason: {tool_result.message}"
            ),
        )
    )

    return tool_result


def build_support_response(
    *,
    start_time: float,
    request_id: str,
    intent: str,
    request: SupportRequest,
    assistant_response: str,
    status: str,
    reason: str,
    eligible: bool,
    tool_result: ToolExecutionResult,
    citations: list[Citation],
    trace: list[AgentTraceStep],
    order_id: str | None = None,
    customer_id: str | None = None,
) -> SupportResponse:
    """Build and persist a consistent support API response."""

    response = SupportResponse(
        request_id=request_id,
        intent=intent,
        message=request.message,
        assistant_response=assistant_response,
        order_id=order_id,
        customer_id=customer_id,
        status=status,
        reason=reason,
        eligible=eligible,
        latency_ms=calculate_latency_ms(start_time),
        tool_result=tool_result,
        citations=citations,
        trace=trace,
    )

    safely_store_support_response(response)

    return response


def evaluate_workflow(
    intent: str,
    order: dict,
) -> tuple[dict, str]:
    """Evaluate deterministic business rules for an intent."""

    if intent == "damaged_item_request":
        return (
            evaluate_damaged_item_request(order),
            "damaged_item_policy_check",
        )

    if intent == "cancellation_request":
        return (
            evaluate_cancellation_request(order),
            "cancellation_policy_check",
        )

    if intent == "shipping_request":
        return (
            evaluate_shipping_request(order),
            "shipping_policy_check",
        )

    if intent == "late_delivery_request":
        return (
            evaluate_late_delivery_request(order),
            "late_delivery_policy_check",
        )

    return (
        evaluate_refund_eligibility(order),
        "refund_policy_check",
    )


def process_support_request(
    request: SupportRequest,
) -> SupportResponse:
    """Execute the complete enterprise support-agent workflow."""

    start_time = perf_counter()
    request_id = generate_request_id()

    citations: list[Citation] = []

    trace = [
        AgentTraceStep(
            step="request_validation",
            status="completed",
            detail="The support request passed schema validation.",
        )
    ]

    intent = classify_support_intent(
        message=request.message,
        trace=trace,
    )

    if intent == "general_support":
        trace.append(
            AgentTraceStep(
                step="workflow_selection",
                status="completed",
                detail="Selected the human-support escalation workflow.",
            )
        )

        decision = "escalate_to_human"
        reason = (
            "The request does not match a currently supported "
            "automated workflow."
        )

        response_context = (
            "Deterministic workflow result:\n"
            f"{reason}\n\n"
            "The request must be reviewed by a human support agent."
        )

        assistant_response = generate_assistant_response(
            message=request.message,
            context=response_context,
            decision=decision,
            trace=trace,
            response_description=(
                "Generated a user-facing escalation response."
            ),
        )

        tool_result = execute_support_tool(
            decision=decision,
            request_id=request_id,
            customer_id=request.customer_id,
            order_id=request.order_id,
            reason=reason,
            trace=trace,
        )

        trace.append(
            AgentTraceStep(
                step="decision",
                status="completed",
                detail=f"Final decision: {decision}.",
            )
        )

        return build_support_response(
            start_time=start_time,
            request_id=request_id,
            intent=intent,
            request=request,
            assistant_response=assistant_response,
            order_id=request.order_id,
            customer_id=request.customer_id,
            status=decision,
            reason=reason,
            eligible=False,
            tool_result=tool_result,
            citations=citations,
            trace=trace,
        )

    trace.append(
        AgentTraceStep(
            step="workflow_selection",
            status="completed",
            detail=f"Selected the {intent} workflow.",
        )
    )

    if request.order_id is None:
        trace.append(
            AgentTraceStep(
                step="order_lookup",
                status="failed",
                detail="No order ID was provided.",
            )
        )

        decision = "missing_order_id"
        reason = "An order ID is required to process this request."

        response_context = (
            "Deterministic workflow result:\n"
            f"{reason}\n\n"
            "Do not claim that the order was found or modified."
        )

        assistant_response = generate_assistant_response(
            message=request.message,
            context=response_context,
            decision=decision,
            trace=trace,
            response_description=(
                "Generated a user-facing missing-order response."
            ),
        )

        tool_result = execute_support_tool(
            decision=decision,
            request_id=request_id,
            customer_id=request.customer_id,
            order_id=None,
            reason=reason,
            trace=trace,
        )

        trace.append(
            AgentTraceStep(
                step="decision",
                status="completed",
                detail=f"Final decision: {decision}.",
            )
        )

        return build_support_response(
            start_time=start_time,
            request_id=request_id,
            intent=intent,
            request=request,
            assistant_response=assistant_response,
            order_id=None,
            customer_id=request.customer_id,
            status=decision,
            reason=reason,
            eligible=False,
            tool_result=tool_result,
            citations=citations,
            trace=trace,
        )

    order = get_order_by_id(request.order_id)

    if order is None:
        trace.append(
            AgentTraceStep(
                step="order_lookup",
                status="failed",
                detail=f"Order {request.order_id} was not found.",
            )
        )

        decision = "order_not_found"
        reason = "No order record was found for the provided order ID."

        response_context = (
            "Deterministic workflow result:\n"
            f"{reason}\n\n"
            "Ask the customer to verify the order information. "
            "Do not invent an order status."
        )

        assistant_response = generate_assistant_response(
            message=request.message,
            context=response_context,
            decision=decision,
            trace=trace,
            response_description=(
                "Generated a user-facing order-not-found response."
            ),
        )

        tool_result = execute_support_tool(
            decision=decision,
            request_id=request_id,
            customer_id=request.customer_id,
            order_id=request.order_id,
            reason=reason,
            trace=trace,
        )

        trace.append(
            AgentTraceStep(
                step="decision",
                status="completed",
                detail=f"Final decision: {decision}.",
            )
        )

        return build_support_response(
            start_time=start_time,
            request_id=request_id,
            intent=intent,
            request=request,
            assistant_response=assistant_response,
            order_id=request.order_id,
            customer_id=request.customer_id,
            status=decision,
            reason=reason,
            eligible=False,
            tool_result=tool_result,
            citations=citations,
            trace=trace,
        )

    trace.append(
        AgentTraceStep(
            step="order_lookup",
            status="completed",
            detail=f"Order {order['order_id']} was found.",
        )
    )

    identity_result = validate_customer_identity(
        order=order,
        customer_id=request.customer_id,
    )

    if not identity_result["valid"]:
        trace.append(
            AgentTraceStep(
                step="identity_validation",
                status="failed",
                detail=identity_result["reason"],
            )
        )

        decision = "escalate_to_human"
        reason = identity_result["reason"]

        response_context = (
            "Deterministic identity-validation result:\n"
            f"{reason}\n\n"
            "The customer identity could not be verified. "
            "Do not expose order details or claim that any action "
            "has been performed."
        )

        assistant_response = generate_assistant_response(
            message=request.message,
            context=response_context,
            decision=decision,
            trace=trace,
            response_description=(
                "Generated a user-facing identity escalation response."
            ),
        )

        tool_result = execute_support_tool(
            decision=decision,
            request_id=request_id,
            customer_id=request.customer_id,
            order_id=order["order_id"],
            reason=reason,
            trace=trace,
        )

        trace.append(
            AgentTraceStep(
                step="decision",
                status="completed",
                detail=f"Final decision: {decision}.",
            )
        )

        return build_support_response(
            start_time=start_time,
            request_id=request_id,
            intent=intent,
            request=request,
            assistant_response=assistant_response,
            order_id=order["order_id"],
            customer_id=request.customer_id,
            status=decision,
            reason=reason,
            eligible=False,
            tool_result=tool_result,
            citations=citations,
            trace=trace,
        )

    trace.append(
        AgentTraceStep(
            step="identity_validation",
            status="completed",
            detail=identity_result["reason"],
        )
    )

    if intent == "order_status":
        decision = "order_status_found"
        reason = f"The current order status is {order['status']}."

        trace.append(
            AgentTraceStep(
                step="order_status_check",
                status="completed",
                detail=reason,
            )
        )

        response_context = (
            "Verified order information:\n"
            f"Order ID: {order['order_id']}\n"
            f"Current status: {order['status']}\n\n"
            "Only explain the verified current status. "
            "Do not claim that the status was changed."
        )

        assistant_response = generate_assistant_response(
            message=request.message,
            context=response_context,
            decision=decision,
            trace=trace,
            response_description=(
                "Generated a user-facing order-status response."
            ),
        )

        tool_result = execute_support_tool(
            decision=decision,
            request_id=request_id,
            customer_id=order["customer_id"],
            order_id=order["order_id"],
            reason=reason,
            trace=trace,
        )

        trace.append(
            AgentTraceStep(
                step="decision",
                status="completed",
                detail="Returned the verified order status.",
            )
        )

        return build_support_response(
            start_time=start_time,
            request_id=request_id,
            intent=intent,
            request=request,
            assistant_response=assistant_response,
            order_id=order["order_id"],
            customer_id=order["customer_id"],
            status=decision,
            reason=reason,
            eligible=False,
            tool_result=tool_result,
            citations=citations,
            trace=trace,
        )

    policy_result = retrieve_policy_context(
        intent=intent,
        query=request.message,
        top_k=settings.rag_top_k,
        minimum_score=settings.rag_minimum_score,
    )

    selected_sources = policy_result["selected_sources"]

    trace.append(
        AgentTraceStep(
            step="policy_scope_selection",
            status="completed",
            detail=(
                f"Selected {len(selected_sources)} policy documents "
                f"for the {intent} workflow: "
                f"{', '.join(selected_sources)}."
            ),
        )
    )

    retrieved_chunks = policy_result["chunks"]

    if not retrieved_chunks:
        trace.append(
            AgentTraceStep(
                step="policy_retrieval",
                status="failed",
                detail=(
                    "No semantic policy result passed the configured "
                    "minimum similarity threshold."
                ),
            )
        )

        decision = "escalate_to_human"
        reason = (
            "No sufficiently relevant policy information could be "
            "retrieved, so the request requires human review."
        )

        response_context = (
            "Retrieval result:\n"
            "No sufficiently relevant policy context was retrieved.\n\n"
            "Deterministic workflow result:\n"
            f"{reason}\n\n"
            "Do not infer or invent a company policy."
        )

        assistant_response = generate_assistant_response(
            message=request.message,
            context=response_context,
            decision=decision,
            trace=trace,
            response_description=(
                "Generated a user-facing policy-retrieval "
                "escalation response."
            ),
        )

        tool_result = execute_support_tool(
            decision=decision,
            request_id=request_id,
            customer_id=order["customer_id"],
            order_id=order["order_id"],
            reason=reason,
            trace=trace,
        )

        trace.append(
            AgentTraceStep(
                step="decision",
                status="completed",
                detail=f"Final decision: {decision}.",
            )
        )

        return build_support_response(
            start_time=start_time,
            request_id=request_id,
            intent=intent,
            request=request,
            assistant_response=assistant_response,
            order_id=order["order_id"],
            customer_id=order["customer_id"],
            status=decision,
            reason=reason,
            eligible=False,
            tool_result=tool_result,
            citations=citations,
            trace=trace,
        )

    for chunk in retrieved_chunks:
        citations.append(
            Citation(
                source=chunk["source"],
                reference=f"chunk_{chunk['chunk_id']}",
                excerpt=build_citation_excerpt(
                    chunk["content"],
                ),
            )
        )

    retrieved_sources = sorted(
        {
            chunk["source"]
            for chunk in retrieved_chunks
        }
    )

    trace.append(
        AgentTraceStep(
            step="policy_retrieval",
            status="completed",
            detail=(
                f"Retrieved {len(retrieved_chunks)} semantic policy "
                f"chunks from {', '.join(retrieved_sources)}. "
                f"Highest similarity score: "
                f"{policy_result['highest_score']}."
            ),
        )
    )

    workflow_result, policy_check_step = evaluate_workflow(
        intent=intent,
        order=order,
    )

    trace.append(
        AgentTraceStep(
            step=policy_check_step,
            status="completed",
            detail=workflow_result["reason"],
        )
    )

    decision = workflow_result["decision"]
    reason = workflow_result["reason"]
    eligible = workflow_result["eligible"]

    retrieved_policy_context = policy_result["context"]

    response_context = (
        "Deterministic business-rule result:\n"
        f"Decision: {decision}\n"
        f"Reason: {reason}\n"
        f"Eligible: {eligible}\n\n"
        "Retrieved policy context:\n"
        f"{retrieved_policy_context}\n\n"
        "The deterministic decision takes priority over the retrieved "
        "text. Use the retrieved policy only to explain the decision."
    )

    if decision == "shipping_information_provided":
        response_context = (
            "Verified shipping result:\n"
            f"{reason}\n\n"
            "Retrieved policy context:\n"
            f"{retrieved_policy_context}\n\n"
            "Only explain the verified shipping information. "
            "Do not claim that the shipment was changed or expedited."
        )

    assistant_response = generate_assistant_response(
        message=request.message,
        context=response_context,
        decision=decision,
        trace=trace,
        response_description=(
            "Generated a user-facing response grounded in "
            "semantic policy context and deterministic business rules."
        ),
    )

    tool_result = execute_support_tool(
        decision=decision,
        request_id=request_id,
        customer_id=order["customer_id"],
        order_id=order["order_id"],
        reason=reason,
        trace=trace,
    )

    trace.append(
        AgentTraceStep(
            step="decision",
            status="completed",
            detail=f"Final decision: {decision}.",
        )
    )

    return build_support_response(
        start_time=start_time,
        request_id=request_id,
        intent=intent,
        request=request,
        assistant_response=assistant_response,
        order_id=order["order_id"],
        customer_id=order["customer_id"],
        status=decision,
        reason=reason,
        eligible=eligible,
        tool_result=tool_result,
        citations=citations,
        trace=trace,
    )