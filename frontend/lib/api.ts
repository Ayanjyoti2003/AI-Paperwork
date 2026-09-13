/**
 * Client API services connecting the Next.js frontend to the FastAPI Paperwork Agent backend.
 */

import type {
  DocumentItem,
  DocumentUploadResponse,
  PreparedPackageResponse,
  ReadinessAssessment,
  WorkflowSummary,
} from "./types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/+$/, "") || "http://127.0.0.1:8000";

/**
 * Custom error class with status and backend detail.
 */
export class ApiError extends Error {
  status: number;
  detail?: string;

  constructor(status: number, message: string, detail?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let errorDetail = "";
    try {
      const errData = await response.json();
      errorDetail =
        typeof errData.detail === "string"
          ? errData.detail
          : JSON.stringify(errData.detail || errData);
    } catch {
      errorDetail = response.statusText;
    }
    throw new ApiError(
      response.status,
      errorDetail || `API request failed with status ${response.status}`,
      errorDetail
    );
  }
  return response.json() as Promise<T>;
}

/**
 * Health check endpoint. Does not require any credentials.
 */
export async function fetchHealth(): Promise<{ status: string }> {
  const res = await fetch(`${API_BASE_URL}/api/health`, {
    method: "GET",
    headers: { Accept: "application/json" },
  });
  return handleResponse<{ status: string }>(res);
}

/**
 * List available workflow definitions from the backend registry.
 */
export async function fetchWorkflows(): Promise<WorkflowSummary[]> {
  const res = await fetch(`${API_BASE_URL}/api/workflows`, {
    method: "GET",
    headers: { Accept: "application/json" },
  });
  return handleResponse<WorkflowSummary[]>(res);
}

/**
 * List documents currently available in the document vault.
 */
export async function fetchDocuments(): Promise<{
  count: number;
  documents: DocumentItem[];
}> {
  const res = await fetch(`${API_BASE_URL}/api/documents`, {
    method: "GET",
    headers: { Accept: "application/json" },
  });
  return handleResponse<{ count: number; documents: DocumentItem[] }>(res);
}

/**
 * Safely upload a document file to the backend document store.
 */
export async function uploadDocument(
  file: File
): Promise<DocumentUploadResponse> {
  const formData = new FormData();
  formData.append("file", file, file.name);

  const res = await fetch(`${API_BASE_URL}/api/documents/upload`, {
    method: "POST",
    body: formData,
  });
  return handleResponse<DocumentUploadResponse>(res);
}

/**
 * Assess paperwork readiness against target workflow requirements.
 */
export async function assessPaperwork(
  userGoal: string
): Promise<ReadinessAssessment> {
  const res = await fetch(`${API_BASE_URL}/api/assess`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify({ user_goal: userGoal }),
  });
  return handleResponse<ReadinessAssessment>(res);
}

/**
 * Prepare an approved application package and Markdown summary from an existing assessment.
 *
 * Deterministic, reproducible, and does not re-invoke the agent.
 */
export async function preparePackage(
  assessment: ReadinessAssessment,
  applicantName?: string,
  notes?: string
): Promise<PreparedPackageResponse> {
  const res = await fetch(`${API_BASE_URL}/api/package/prepare`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify({
      assessment,
      applicant_name: applicantName || null,
      notes: notes || null,
    }),
  });
  return handleResponse<PreparedPackageResponse>(res);
}
