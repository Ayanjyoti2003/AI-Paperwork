/**
 * Client API services connecting the Next.js frontend to the FastAPI Paperwork Agent backend.
 */

import type {
  DocumentListResponse,
  DocumentUploadResponse,
  PreparedPackageResponse,
  ReadinessAssessment,
  WorkflowSummary,
} from "./types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/+$/, "") || "http://127.0.0.1:8000";

interface BackendValidationError {
  msg?: string;
  [key: string]: unknown;
}

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
      if (typeof errData.detail === "string") {
        errorDetail = errData.detail;
      } else if (Array.isArray(errData.detail)) {
        errorDetail = errData.detail
          .map((e: BackendValidationError) => e.msg || JSON.stringify(e))
          .join("; ");
      } else {
        errorDetail = JSON.stringify(errData.detail || errData);
      }
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
    cache: "no-store",
  });
  return handleResponse<{ status: string }>(res);
}
export const checkHealth = fetchHealth;

/**
 * List available workflow definitions from the backend registry.
 */
export async function fetchWorkflows(): Promise<WorkflowSummary[]> {
  const res = await fetch(`${API_BASE_URL}/api/workflows`, {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  return handleResponse<WorkflowSummary[]>(res);
}
export const getWorkflows = fetchWorkflows;

/**
 * List documents currently available in the document vault.
 */
export async function fetchDocuments(): Promise<DocumentListResponse> {
  const res = await fetch(`${API_BASE_URL}/api/documents`, {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  return handleResponse<DocumentListResponse>(res);
}
export const getDocuments = fetchDocuments;

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
 * Delete a document from the local store by its document ID.
 */
export async function deleteDocument(
  documentId: string
): Promise<{ status: string; document_id: string; filename: string }> {
  const res = await fetch(
    `${API_BASE_URL}/api/documents/${encodeURIComponent(documentId)}`,
    {
      method: "DELETE",
    }
  );
  return handleResponse<{ status: string; document_id: string; filename: string }>(res);
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
