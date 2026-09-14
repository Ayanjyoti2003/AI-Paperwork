import type {
  DocumentListResponse,
  DocumentUploadResponse,
  ReadinessAssessment,
  WorkflowSummary,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

interface BackendValidationError {
  msg?: string;
  [key: string]: unknown;
}

/**
 * Helper to parse backend error response.
 */
async function parseError(response: Response): Promise<string> {
  try {
    const data = await response.json();
    if (data?.detail) {
      if (typeof data.detail === "string") return data.detail;
      if (Array.isArray(data.detail)) {
        return data.detail
          .map((e: BackendValidationError) => e.msg || JSON.stringify(e))
          .join("; ");
      }
      return JSON.stringify(data.detail);
    }
  } catch {
    // ignore parse error and return statusText
  }
  return response.statusText || `Request failed with status ${response.status}`;
}

/**
 * Health check endpoint.
 */
export async function checkHealth(): Promise<{ status: string }> {
  const res = await fetch(`${API_BASE}/api/health`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(await parseError(res));
  }
  return res.json();
}

/**
 * Retrieve the list of documents available in the local document store.
 */
export async function getDocuments(): Promise<DocumentListResponse> {
  const res = await fetch(`${API_BASE}/api/documents`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(await parseError(res));
  }
  return res.json();
}

/**
 * Upload a supported file to the local document store.
 */
export async function uploadDocument(file: File): Promise<DocumentUploadResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API_BASE}/api/documents/upload`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const errorMsg = await parseError(res);
    throw new Error(errorMsg);
  }

  return res.json();
}

/**
 * Delete a document from the local store by its document ID.
 */
export async function deleteDocument(
  documentId: string
): Promise<{ status: string; document_id: string; filename: string }> {
  const res = await fetch(`${API_BASE}/api/documents/${encodeURIComponent(documentId)}`, {
    method: "DELETE",
  });

  if (!res.ok) {
    throw new Error(await parseError(res));
  }

  return res.json();
}

/**
 * List available workflow definitions.
 */
export async function getWorkflows(): Promise<WorkflowSummary[]> {
  const res = await fetch(`${API_BASE}/api/workflows`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(await parseError(res));
  }
  return res.json();
}

/**
 * Run paperwork assessment for a natural language goal.
 */
export async function assessPaperwork(userGoal: string): Promise<ReadinessAssessment> {
  const res = await fetch(`${API_BASE}/api/assess`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ user_goal: userGoal }),
  });

  if (!res.ok) {
    const errorMsg = await parseError(res);
    throw new Error(errorMsg);
  }

  return res.json();
}
