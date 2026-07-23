import type {
  SupportRequest,
  SupportResponse,
} from "../types/support";

const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || "/api"
).replace(/\/+$/, "");

const SUPPORT_ENDPOINT = `${API_BASE_URL}/support/analyse`;

export async function analyseSupportRequest(
  request: SupportRequest,
): Promise<SupportResponse> {
  const response = await fetch(SUPPORT_ENDPOINT, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    let errorMessage = "The support request could not be processed.";

    try {
      const errorBody = (await response.json()) as {
        detail?: string;
        message?: string;
      };

      errorMessage =
        errorBody.detail ||
        errorBody.message ||
        `Request failed with status ${response.status}.`;
    } catch {
      errorMessage = `Request failed with status ${response.status}.`;
    }

    throw new Error(errorMessage);
  }

  return (await response.json()) as SupportResponse;
}