export type TraceStatus = "completed" | "skipped" | "failed";

export interface AgentTraceStep {
  step: string;
  status: TraceStatus;
  detail: string;
}

export interface Citation {
  source: string;
  reference: string;
  excerpt: string;
}

export interface ToolExecutionResult {
  tool_name: string;
  status: TraceStatus;
  executed: boolean;
  reference_id: string | null;
  message: string;
  data: Record<string, unknown>;
}

export interface SupportRequest {
  message: string;
  order_id: string | null;
  customer_id: string | null;
}

export interface SupportResponse {
  request_id: string;
  intent: string;
  message: string;
  assistant_response: string;
  order_id: string | null;
  customer_id: string | null;
  status: string;
  reason: string;
  eligible: boolean;
  latency_ms: number;
  tool_result: ToolExecutionResult;
  citations: Citation[];
  trace: AgentTraceStep[];
}