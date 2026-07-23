# Escalation Policy

## Purpose

The escalation process ensures that requests requiring judgement, manual action, additional verification, or elevated authority are transferred to a human support agent.

## Automatic Escalation Conditions

A request must be escalated when:

- The customer identity cannot be verified.
- The order record cannot be found.
- Required order or delivery information is missing.
- The available policy documents do not clearly cover the request.
- The customer provides conflicting or inconsistent information.
- The request involves a high-value, restricted, personalised, or safety-sensitive product.
- The requested action cannot be executed by the AI support agent.
- The customer explicitly asks to speak with a human support agent.

## Financial Escalation

The request must be escalated when:

- A refund amount exceeds the authorised automation limit.
- A partial refund requires manual calculation.
- A payment dispute or chargeback is mentioned.
- The customer claims that an expected refund has not arrived.
- Compensation, store credit, or goodwill payment is requested.

## Delivery Escalation

The request must be escalated when:

- A package is marked as delivered but the customer reports that it was not received.
- The carrier marks the package as lost.
- Tracking information has not updated for more than 3 business days.
- The delivery address appears incorrect after shipment.
- Multiple items from the same order have different delivery outcomes.

## Safety and Sensitive Cases

The request must be escalated immediately when:

- The customer reports an injury, fire, electrical issue, contamination, or another safety risk.
- The request contains threats, abuse, fraud indicators, or suspected account compromise.
- The customer shares sensitive personal or payment information that should not be processed automatically.

## Escalation Priority

Escalated requests may be assigned one of the following priority levels:

- `standard`: Manual review is required, but there is no urgent risk.
- `high`: Financial loss, delivery failure, or account security may be involved.
- `urgent`: A safety issue, suspected fraud, or serious customer impact is reported.

## AI Agent Limitations

The AI support agent may:

- Identify that human review is required.
- Explain why the request is being escalated.
- Collect the minimum information needed for review.
- Recommend an escalation priority.

The AI support agent must not:

- Issue a refund or compensation directly.
- Modify payment or account-security information.
- Contact a delivery carrier.
- Make legal or safety determinations.
- Guarantee the outcome of a human review.