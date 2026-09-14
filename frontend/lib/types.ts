export type Tone = "success" | "warning" | "danger" | "info" | "neutral";

export type RequirementStatus = "verified" | "missing" | "review";

export type Requirement = {
  label: string;
  detail: string;
  status: RequirementStatus;
  action: string;
};

// ---------------------------------------------------------------------------
// Backend Paperwork Agent API Types
// ---------------------------------------------------------------------------

export type DocumentFact = {
  field: string;
  value: string | null;
  source_document: string;
  source_page?: number | null;
  page_number?: number | null;
  confidence: string | number;
  evidence_snippet?: string | null;
  extraction_method?: string | null;
};

export type ConflictValue = {
  source_document: string;
  value: string;
};

export type ConflictDetail = {
  field: string;
  values: ConflictValue[];
};

export type RequirementCheck = {
  requirement_id: string;
  requirement_name: string;
  status: "satisfied" | "missing" | "conflict" | "uncertain";
  evidence: DocumentFact[];
  conflicts: ConflictDetail[];
  notes?: string | null;
};

export type ReadinessAssessment = {
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
};

export type WorkflowSummary = {
  workflow_id: string;
  workflow_name: string;
  description: string;
  requirements_count: number;
};

export type DocumentItem = {
  document_id: string;
  filename: string;
  file_type: string;
  size_bytes: number;
  modified_at?: string | null;
  extraction_method?: string | null;
};

export type DocumentListResponse = {
  documents: DocumentItem[];
  count: number;
};

export type DocumentUploadResponse = {
  document_id?: string;
  filename: string;
  original_filename?: string;
  file_type?: string;
  size_bytes: number;
  modified_at?: string;
  message: string;
};

export type PreparedPackageResponse = {
  package_id: string;
  approved: boolean;
  workflow_id: string;
  workflow_name: string;
  ready: boolean;
  package: Record<string, unknown>;
  markdown_summary: string;
};

