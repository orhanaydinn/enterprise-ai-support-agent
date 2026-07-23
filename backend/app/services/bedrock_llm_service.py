import json

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from pydantic import ValidationError

from app.core.config import settings
from app.models.intents import IntentClassification
from app.services.llm_service import LLMProvider

from dataclasses import dataclass

@dataclass(frozen=True)
class BedrockResponseResult:
    """Represent generated text and its final response source."""

    text: str
    source: str
    safety_reason: str | None = None

class BedrockLLMProvider(LLMProvider):
    """Provide intent classification and response generation through Bedrock."""

    FORBIDDEN_EXECUTION_PHRASES = {
        "we will proceed",
        "we have processed",
        "has been processed",
        "has been cancelled",
        "has been refunded",
        "refund has been issued",
        "cancellation is complete",
        "replacement has been created",
        "you will receive a confirmation email",
        "the money will be returned",
        "we look into this",
        "we'll look into this",
        "we will look into this",
        "while we investigate",
        "we are investigating",
        "we'll investigate",
        "we will investigate",
        "please wait while",
        "a support agent will contact you",
        "support will contact you",
        "we will contact you",
        "will contact you shortly",
        "cancellation request has been approved",
        "you will receive further updates",
        "further updates regarding this cancellation",
    }

    UNAUTHORIZED_ESCALATION_PHRASES = {
        "human review",
        "human support",
        "human agent",
        "support representative",
        "support agent",
        "customer service representative",
        "requires escalation",
        "require escalation",
        "needs escalation",
        "escalate this",
    }

    def __init__(
        self,
        region_name: str = settings.aws_region,
        model_id: str = settings.bedrock_model_id,
    ) -> None:
        """Initialize the Amazon Bedrock Runtime client."""

        self.region_name = region_name
        self.model_id = model_id

        self.client = boto3.client(
            "bedrock-runtime",
            region_name=region_name,
        )

    def classify_intent(
        self,
        message: str,
    ) -> IntentClassification:
        """Classify a support request using validated structured output."""

        system_prompt = (
            "You classify customer-support messages for an enterprise "
            "support application. "
            "Return exactly one JSON object and no additional text. "
            "Do not use Markdown or code fences. "
            "The intent must be exactly one of these values: "
            "refund_request, damaged_item_request, "
            "cancellation_request, shipping_request, "
            "late_delivery_request, order_status, general_support. "
            "Use late_delivery_request when a customer says an existing "
            "shipment is late, stuck, delayed, has not moved, or has no "
            "tracking updates. "
            "Use shipping_request for general shipping questions such as "
            "delivery times, shipping methods, tracking availability, or "
            "shipping costs when no existing delay is reported. "
            "Use order_status when the customer asks for the current "
            "state of a specific order without reporting another issue. "
            "Use refund_request when the customer asks for a refund or "
            "money back. "
            "Use damaged_item_request when the customer reports a broken, "
            "damaged, defective, or unusable item. "
            "Use cancellation_request when the customer asks to stop or "
            "cancel an existing order. "
            "Use general_support only when none of the supported intents "
            "clearly applies."
        )

        user_prompt = (
            "Classify the following customer message.\n\n"
            f"Customer message:\n{message}\n\n"
            "Return this exact JSON structure:\n"
            "{\n"
            '  "intent": "one_allowed_intent",\n'
            '  "confidence": 0.0,\n'
            '  "reason": "short classification reason"\n'
            "}"
        )

        try:
            response = self.client.converse(
                modelId=self.model_id,
                system=[
                    {
                        "text": system_prompt,
                    }
                ],
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "text": user_prompt,
                            }
                        ],
                    }
                ],
                inferenceConfig={
                    "maxTokens": 160,
                    "temperature": 0.0,
                },
            )

            output_text = self._extract_response_text(response)
            json_text = self._extract_json_object(output_text)
            parsed_output = json.loads(json_text)

            return IntentClassification.model_validate(parsed_output)

        except ClientError as error:
            error_details = error.response.get("Error", {})
            error_code = error_details.get("Code", "Unknown")
            error_message = error_details.get(
                "Message",
                str(error),
            )

            raise RuntimeError(
                "Amazon Bedrock intent classification failed: "
                f"{error_code} - {error_message}"
            ) from error

        except BotoCoreError as error:
            raise RuntimeError(
                "Amazon Bedrock SDK intent classification failed: "
                f"{error}"
            ) from error

        except json.JSONDecodeError as error:
            raise RuntimeError(
                "Amazon Bedrock returned invalid JSON for intent "
                "classification."
            ) from error

        except ValidationError as error:
            raise RuntimeError(
                "Amazon Bedrock returned an invalid intent "
                "classification structure."
            ) from error

        except (KeyError, TypeError, ValueError) as error:
            raise RuntimeError(
                "Amazon Bedrock returned an unexpected intent "
                "classification response."
            ) from error

    def generate_response(
        self,
        message: str,
        context: str,
        decision: str,
    ) -> str:
        """Generate a short response grounded in validated context."""

        result = self.generate_response_result(
            message=message,
            context=context,
            decision=decision,
        )

        return result.text


    def generate_response_result(
        self,
        message: str,
        context: str,
        decision: str,
    ) -> BedrockResponseResult:
        """Generate a response and report its final source."""

        system_prompt = (
            "You are an enterprise customer-support assistant. "
            "A separate deterministic rules engine has already validated "
            "the customer, retrieved the relevant policies, and produced "
            "the final decision. You must not change that decision. "
            "You only explain the decision to the customer. "
            "You cannot execute refunds, cancellations, replacements, "
            "shipments, compensation, account changes, emails, or any "
            "other real-world action. "
            "Never claim or imply that an action has been completed, "
            "scheduled, initiated, submitted, or guaranteed. "
            "Never promise a confirmation email or a future outcome. "
            "Do not recommend or imply human escalation unless the "
            "validated decision is exactly 'escalate_to_human'. "
            "Use cautious wording such as 'appears eligible', "
            "'may be reviewed', or 'requires human review' only when "
            "consistent with the validated decision. "
            "Answer in concise, professional English using no more than "
            "three short sentences."
        )

        user_prompt = (
            f"Customer message:\n{message}\n\n"
            f"Validated decision:\n{decision}\n\n"
            f"Approved context:\n{context}\n\n"
            "Write only the customer-facing response. "
            "Do not add headings, analysis, policy citations, or "
            "internal workflow details."
        )

        try:
            response = self.client.converse(
                modelId=self.model_id,
                system=[
                    {
                        "text": system_prompt,
                    }
                ],
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "text": user_prompt,
                            }
                        ],
                    }
                ],
                inferenceConfig={
                    "maxTokens": 160,
                    "temperature": 0.0,
                },
            )

            output_text = self._extract_response_text(response)

            if self._contains_execution_claim(output_text):
                return BedrockResponseResult(
                    text=self._build_safe_fallback(
                        decision=decision,
                        context=context,
                    ),
                    source="deterministic_safety_fallback",
                    safety_reason="execution_claim_detected",
                )

            if self._contains_unauthorized_escalation(
                response=output_text,
                decision=decision,
            ):
                return BedrockResponseResult(
                    text=self._build_safe_fallback(
                        decision=decision,
                        context=context,
                    ),
                    source="deterministic_safety_fallback",
                    safety_reason="unauthorized_escalation_detected",
                )

            return BedrockResponseResult(
                text=output_text,
                source="amazon_bedrock",
            )

        except ClientError as error:
            error_details = error.response.get("Error", {})
            error_code = error_details.get("Code", "Unknown")
            error_message = error_details.get(
                "Message",
                str(error),
            )

            raise RuntimeError(
                "Amazon Bedrock request failed: "
                f"{error_code} - {error_message}"
            ) from error

        except BotoCoreError as error:
            raise RuntimeError(
                f"Amazon Bedrock SDK request failed: {error}"
            ) from error

        except (KeyError, TypeError) as error:
            raise RuntimeError(
                "Amazon Bedrock returned an unexpected response format."
            ) from error
        
    def _extract_response_text(self, response: dict) -> str:
        """Extract text content from a Bedrock Converse response."""

        content_blocks = response["output"]["message"]["content"]

        output_text = "".join(
            block.get("text", "")
            for block in content_blocks
            if "text" in block
        ).strip()

        if not output_text:
            raise RuntimeError(
                "Amazon Bedrock returned an empty response."
            )

        return output_text

    def _extract_json_object(self, output_text: str) -> str:
        """Extract the first complete JSON object from model output."""

        cleaned_text = output_text.strip()

        if cleaned_text.startswith("```"):
            cleaned_text = cleaned_text.replace(
                "```json",
                "",
                1,
            )
            cleaned_text = cleaned_text.replace(
                "```",
                "",
                1,
            )
            cleaned_text = cleaned_text.strip()

        start_index = cleaned_text.find("{")
        end_index = cleaned_text.rfind("}")

        if start_index == -1 or end_index == -1:
            raise ValueError(
                "No JSON object was found in the model output."
            )

        if end_index <= start_index:
            raise ValueError(
                "The JSON object in the model output is incomplete."
            )

        return cleaned_text[start_index:end_index + 1]

    def _contains_execution_claim(
        self,
        response: str,
    ) -> bool:
        """Detect claims that an external action was or will be executed."""

        normalized_response = response.lower()

        return any(
            phrase in normalized_response
            for phrase in self.FORBIDDEN_EXECUTION_PHRASES
        )

    def _contains_unauthorized_escalation(
        self,
        response: str,
        decision: str,
    ) -> bool:
        """Detect escalation language that conflicts with the final decision."""

        if decision == "escalate_to_human":
            return False

        normalized_response = response.lower()

        return any(
            phrase in normalized_response
            for phrase in self.UNAUTHORIZED_ESCALATION_PHRASES
        )

    def _build_safe_fallback(
        self,
        decision: str,
        context: str,
    ) -> str:
        """Return a deterministic response when model output is unsafe."""

        if decision == "approve_cancellation":
            return (
                "Your order appears eligible for cancellation based on "
                "its current fulfilment status. No cancellation has been "
                "executed."
            )

        if decision == "approve_refund":
            return (
                "Your order appears eligible for a refund based on the "
                "verified order details. No refund has been issued."
            )

        if decision == "request_damage_evidence":
            return (
                "Please provide a description of the damage and "
                "photographic evidence when available so the request "
                "can be reviewed."
            )

        if decision == "cancellation_not_available":
            return (
                "This order does not appear eligible for automatic "
                "cancellation because fulfilment has already progressed."
            )

        if decision == "delivery_delayed":
            return (
                "Your order appears to be delayed because it is still "
                "marked as shipped and the tracking has not updated as "
                "expected. Please check the latest carrier tracking "
                "information and the estimated delivery date."
            )

        if decision == "escalate_to_human":
            return (
                "This request requires review by a human support agent."
            )

        if decision == "missing_order_id":
            return (
                "An order ID is required to process this request. "
                "Please provide the relevant order ID."
            )

        if decision == "order_not_found":
            return (
                "No order record was found for the provided order ID. "
                "Please verify the order information and try again."
            )

        if decision == "order_status_found":
            return context

        if decision == "shipping_information_provided":
            return context

        return context