"""Paperwork Agent - Pydantic schemas for documents, requirements, and assessments."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional, Union

from pydantic import BaseModel, Field, model_validator


# --- Document Schemas ---

class Document(BaseModel):
    """Metadata for a document in the local store."""

    document_id: str = Field(description="Stable identifier derived from filename")
    filename: str = Field(description="Original filename")
    file_type: str = Field(description="File extension (e.g., txt, md, json, pdf, png, jpg)")
    size_bytes: int = Field(description="File size in bytes")
    modified_at: Optional[str] = Field(default=None, description="Last modified timestamp")
    extraction_method: Optional[str] = Field(
        default=None, description="native_text, local_ocr, or textract"
    )


class DocumentSearchResult(BaseModel):
    """A single search hit."""

    document_id: str
    filename: str
    snippet: str = Field(description="Relevant text snippet")
    relevance_score: float = Field(description="0.0 to 1.0 relevance score")


class DocumentFact(BaseModel):
    """A single factual field extracted from a document with provenance."""

    field: str = Field(description="Name of the factual field (e.g., 'date_of_birth')")
    value: Optional[str] = Field(default=None, description="Extracted value, None if not found")
    source_document: str = Field(description="Document ID the fact was extracted from")
    source_page: Optional[int] = Field(default=None, description="Page number if applicable")
    page_number: Optional[int] = Field(default=None, description="Page number if applicable")
    confidence: Union[str, float] = Field(
        default="high", description="high, medium, low, not_found, or numeric OCR confidence"
    )
    evidence_snippet: Optional[str] = Field(
        default=None, description="Verbatim snippet supporting the extraction"
    )
    extraction_method: Optional[str] = Field(
        default="native_text", description="native_text, local_ocr, or textract"
    )

    @model_validator(mode="after")
    def sync_page_numbers(self) -> DocumentFact:
        if self.source_page is None and self.page_number is not None:
            self.source_page = self.page_number
        elif self.page_number is None and self.source_page is not None:
            self.page_number = self.source_page
        return self


# --- Requirement Schemas ---

class Requirement(BaseModel):
    """A single requirement in a workflow."""

    id: str
    name: str
    description: str
    required: bool = True
    accepted_evidence_types: list[str] = Field(
        default_factory=list,
        description="Types of documents or evidence that satisfy this requirement",
    )
    relevant_fields: list[str] = Field(
        default_factory=list,
        description="Factual fields to look for (e.g., 'full_name', 'date_of_birth')",
    )
    validation_hints: Optional[str] = Field(
        default=None,
        description="Human/agent guidance for validating this requirement (e.g. freshness, issuing body)",
    )


class Workflow(BaseModel):
    """A workflow definition containing its requirements."""

    workflow_id: str
    workflow_name: str
    description: str
    requirements: list[Requirement]


class WorkflowDiscoveryResult(BaseModel):
    """Result of attempting to discover a matching workflow for a user goal."""

    status: str = Field(description="'found' if a workflow was matched, 'workflow_not_found' otherwise")
    workflow_id: Optional[str] = Field(default=None, description="Matching workflow ID")
    workflow_name: Optional[str] = Field(default=None, description="Human-readable workflow name")
    confidence: float = Field(default=0.0, description="Match confidence score between 0.0 and 1.0")
    reason: str = Field(default="", description="Explanation of why this workflow was matched or why search failed")
    available_workflows: list[dict[str, str]] = Field(
        default_factory=list, description="List of available workflow IDs and names if not found"
    )


# --- Evidence Schemas ---

class EvidenceBundle(BaseModel):
    """Structured collection of facts gathered during a paperwork verification workflow."""

    workflow_id: str = Field(description="The workflow ID this evidence is gathered for")
    facts: list[DocumentFact] = Field(default_factory=list, description="All extracted facts with provenance")
    source_documents: list[str] = Field(default_factory=list, description="List of source document IDs or filenames")
    extraction_notes: Optional[str] = Field(default=None, description="Observations or notes regarding the extraction")


# --- Verification Schemas ---

class RequirementStatus(str, Enum):
    """Status of a single requirement check."""

    SATISFIED = "satisfied"
    MISSING = "missing"
    CONFLICT = "conflict"
    UNCERTAIN = "uncertain"


class ConflictDetail(BaseModel):
    """Details about a conflicting fact across documents."""

    field: str
    values: list[dict[str, str]] = Field(
        description="List of {source_document, value} pairs showing conflicting values"
    )


class RequirementCheck(BaseModel):
    """Result of checking a single requirement against evidence."""

    requirement_id: str
    requirement_name: str
    status: RequirementStatus
    evidence: list[DocumentFact] = Field(default_factory=list)
    conflicts: list[ConflictDetail] = Field(default_factory=list)
    notes: Optional[str] = None


class ReadinessAssessment(BaseModel):
    """Final assessment of paperwork readiness for a workflow."""

    workflow_id: str
    workflow_name: str
    ready: bool = Field(description="True if all required requirements are satisfied without conflicts")
    completion_percentage: float = Field(description="Percentage of requirements satisfied")
    satisfied_requirements: list[RequirementCheck] = Field(default_factory=list)
    missing_requirements: list[RequirementCheck] = Field(default_factory=list)
    conflicts: list[RequirementCheck] = Field(default_factory=list)
    uncertainties: list[RequirementCheck] = Field(default_factory=list)
    recommended_next_actions: list[str] = Field(default_factory=list)
    assessed_at: str = Field(default_factory=lambda: datetime.now().isoformat())
