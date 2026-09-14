export type Tone = "success" | "warning" | "danger" | "info" | "neutral";

export type RequirementStatus = "verified" | "missing" | "review";

export type Requirement = {
  label: string;
  detail: string;
  status: RequirementStatus;
  action: string;
};

// --- Backend API Types ---

export interface DocumentItem {
  document_id: string;
  filename: string;
  file_type: string;
  size_bytes: number;
  modified_at?: string | null;
}

export interface DocumentListResponse {
  documents: DocumentItem[];
  count: number;
}

export interface DocumentUploadResponse {
  document_id: string;
  filename: string;
  original_filename: string;
  file_type: string;
  size_bytes: number;
  modified_at: string;
  message: string;
}

export interface WorkflowSummary {
  workflow_id: string;
  workflow_name: string;
  description: string;
  requirements_count: number;
}

export interface DocumentFact {
  field: string;
  value?: string | null;
  source_document: string;
  source_page?: number | null;
  confidence: string;
  evidence_snippet?: string | null;
}

export interface ConflictDetail {
  field: string;
  values: Array<{
    source_document: string;
    value: string;
  }>;
}

export interface RequirementCheck {
  requirement_id: string;
  requirement_name: string;
  status: "satisfied" | "missing" | "conflict" | "uncertain";
  evidence: DocumentFact[];
  conflicts: ConflictDetail[];
  notes?: string | null;
}

export interface ReadinessAssessment {
  workflow_id: string;
  workflow_name: string;
  ready: boolean;
  completion_percentage: number;
  satisfied_requirements: RequirementCheck[];
  missing_requirements: RequirementCheck[];
  conflicts: RequirementCheck[];
  uncertainties: RequirementCheck[];
  recommended_next_actions: string[];
  assessed_at: string;
}
