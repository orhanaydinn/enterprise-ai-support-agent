import { useState } from "react";
import type { FormEvent } from "react";

import { analyseSupportRequest } from "./services/supportApi";
import type {
  SupportRequest,
  SupportResponse,
} from "./types/support";

import "./App.css";

interface ExampleRequest extends SupportRequest {
  label: string;
}

const EXAMPLE_REQUESTS: ExampleRequest[] = [
  {
    label: "Late delivery",
    message: "The parcel has not moved for several days.",
    order_id: "ORD-1002",
    customer_id: "CUS-1002",
  },
  {
    label: "Refund",
    message: "I would like a refund for my delivered order.",
    order_id: "ORD-1001",
    customer_id: "CUS-1001",
  },
  {
    label: "Cancellation",
    message: "I want to cancel my order before it leaves the warehouse.",
    order_id: "ORD-1004",
    customer_id: "CUS-1004",
  },
  {
    label: "Damaged item",
    message: "The product arrived broken.",
    order_id: "ORD-1001",
    customer_id: "CUS-1001",
  },
];

function formatLabel(value: string): string {
  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function App() {
  const [message, setMessage] = useState(
    "The parcel has not moved for several days.",
  );
  const [orderId, setOrderId] = useState("ORD-1002");
  const [customerId, setCustomerId] = useState("CUS-1002");

  const [result, setResult] = useState<SupportResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  function loadExample(example: ExampleRequest): void {
    setMessage(example.message);
    setOrderId(example.order_id ?? "");
    setCustomerId(example.customer_id ?? "");
    setResult(null);
    setError(null);
  }

  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ): Promise<void> {
    event.preventDefault();

    const trimmedMessage = message.trim();

    if (!trimmedMessage) {
      setError("Please enter a customer support message.");
      return;
    }

    setIsLoading(true);
    setError(null);
    setResult(null);

    const request: SupportRequest = {
      message: trimmedMessage,
      order_id: orderId.trim() || null,
      customer_id: customerId.trim() || null,
    };

    try {
      const response = await analyseSupportRequest(request);
      setResult(response);
    } catch (requestError) {
      const errorMessage =
        requestError instanceof Error
          ? requestError.message
          : "An unexpected error occurred.";

      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <main className="app-shell">
      <header className="page-header">
        <div>
          <p className="eyebrow">Enterprise AI Workflow</p>

          <h1>AI Support Agent</h1>

          <p className="subtitle">
            Analyse customer requests using Amazon Bedrock, semantic
            retrieval, deterministic business rules and controlled tool
            execution.
          </p>
        </div>

        <div className="system-status">
          <span />
          System online
        </div>
      </header>

      <section className="dashboard">
        <article className="panel form-panel">
          <div className="panel-header">
            <p>New request</p>
            <h2>Customer message</h2>
          </div>

          <form onSubmit={handleSubmit}>
            <label className="form-field">
              <span>Message</span>

              <textarea
                value={message}
                onChange={(event) => setMessage(event.target.value)}
                rows={7}
              />
            </label>

            <div className="field-grid">
              <label className="form-field">
                <span>Order ID</span>

                <input
                  value={orderId}
                  onChange={(event) => setOrderId(event.target.value)}
                />
              </label>

              <label className="form-field">
                <span>Customer ID</span>

                <input
                  value={customerId}
                  onChange={(event) => setCustomerId(event.target.value)}
                />
              </label>
            </div>

            <button type="submit" disabled={isLoading}>
              {isLoading ? "Analysing request..." : "Run support agent"}
            </button>
          </form>

          <section className="examples-section">
            <p className="examples-label">Example requests</p>

            <div className="example-buttons">
              {EXAMPLE_REQUESTS.map((example) => (
                <button
                  key={example.label}
                  type="button"
                  disabled={isLoading}
                  onClick={() => loadExample(example)}
                >
                  {example.label}
                </button>
              ))}
            </div>
          </section>
        </article>

        <article className="panel result-panel">
          {!result && !error && (
            <div className="empty-state">
              <div className="empty-icon">AI</div>

              <h2>Ready to analyse</h2>

              <p>
                Submit a request to view the assistant response,
                deterministic decision and tool execution result.
              </p>
            </div>
          )}

          {error && (
            <div className="error-state">
              <p>Request failed</p>
              <h2>Unable to analyse the request</h2>
              <span>{error}</span>
            </div>
          )}

          {result && (
            <div className="result-content">
              <div className="result-heading">
                <div>
                  <p>Assistant response</p>
                  <h2>{formatLabel(result.intent)}</h2>
                </div>

                <span className="decision-badge">
                  {formatLabel(result.status)}
                </span>
              </div>

              <div className="assistant-response">
                {result.assistant_response}
              </div>

              <div className="metrics-grid">
                <div>
                  <span>Eligible</span>
                  <strong>{result.eligible ? "Yes" : "No"}</strong>
                </div>

                <div>
                  <span>Latency</span>
                  <strong>{result.latency_ms.toFixed(0)} ms</strong>
                </div>

                <div>
                  <span>Order</span>
                  <strong>{result.order_id ?? "Not provided"}</strong>
                </div>

                <div>
                  <span>Ticket</span>
                  <strong>
                    {result.tool_result.reference_id ?? "Not created"}
                  </strong>
                </div>
              </div>

              <section className="reason-section">
                <h3>Decision reason</h3>
                <p>{result.reason}</p>
              </section>

              <section className="tool-section">
                <div className="section-heading">
                  <div>
                    <p className="section-kicker">Controlled action</p>
                    <h3>Tool execution</h3>
                  </div>

                  <span
                    className={
                      result.tool_result.executed
                        ? "tool-status tool-status-completed"
                        : "tool-status tool-status-skipped"
                    }
                  >
                    {formatLabel(result.tool_result.status)}
                  </span>
                </div>

                <div className="tool-grid">
                  <article className="tool-detail">
                    <span>Tool name</span>
                    <strong>
                      {formatLabel(result.tool_result.tool_name)}
                    </strong>
                  </article>

                  <article className="tool-detail">
                    <span>Reference ID</span>
                    <strong>
                      {result.tool_result.reference_id ?? "Not created"}
                    </strong>
                  </article>

                  <article className="tool-detail">
                    <span>Ticket type</span>
                    <strong>
                      {typeof result.tool_result.data.ticket_type ===
                      "string"
                        ? formatLabel(
                            result.tool_result.data.ticket_type,
                          )
                        : "None"}
                    </strong>
                  </article>

                  <article className="tool-detail">
                    <span>Environment</span>
                    <strong>
                      {result.tool_result.data.simulation === true
                        ? "Simulation"
                        : "Production"}
                    </strong>
                  </article>
                </div>

                <div className="tool-message">
                  <span>Execution message</span>
                  <p>{result.tool_result.message}</p>
                </div>
              </section>

              <section className="citations-section">
                <div className="section-heading">
                  <div>
                    <p className="section-kicker">Retrieved evidence</p>
                    <h3>Policy citations</h3>
                  </div>

                  <span className="citation-count">
                    {result.citations.length}{" "}
                    {result.citations.length === 1 ? "source" : "sources"}
                  </span>
                </div>

                {result.citations.length === 0 ? (
                  <div className="citations-empty">
                    No policy citations were required for this response.
                  </div>
                ) : (
                  <div className="citations-list">
                    {result.citations.map((citation) => (
                      <article
                        className="citation-card"
                        key={`${citation.source}-${citation.reference}`}
                      >
                        <div className="citation-header">
                          <strong>{citation.source}</strong>
                          <span>{citation.reference}</span>
                        </div>

                        <p>{citation.excerpt}</p>
                      </article>
                    ))}
                  </div>
                )}
              </section>

              <section className="trace-section">
                <div className="section-heading">
                  <div>
                    <p className="section-kicker">Observability</p>
                    <h3>Agent trace</h3>
                  </div>

                  <span className="trace-count">
                    {result.trace.length} steps
                  </span>
                </div>

                <div className="trace-list">
                  {result.trace.map((traceStep, index) => (
                    <article
                      className="trace-step"
                      key={`${traceStep.step}-${index}`}
                    >
                      <div className="trace-index">
                        <span>{index + 1}</span>
                      </div>

                      <div className="trace-content">
                        <div className="trace-header">
                          <strong>{formatLabel(traceStep.step)}</strong>

                          <span
                            className={`trace-status trace-status-${traceStep.status}`}
                          >
                            {formatLabel(traceStep.status)}
                          </span>
                        </div>

                        <p>{traceStep.detail}</p>
                      </div>
                    </article>
                  ))}
                </div>
              </section>
            </div>
          )}
        </article>
      </section>
    </main>
  );
}

export default App;