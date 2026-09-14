"""FastAPI Backend API Layer for the Paperwork Agent.

Provides endpoints for health check, workflow discovery, document inspection,
and paperwork readiness assessment. Compatible with local frontend development
via CORS and OpenAPI documentation.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import logging
import os
from pathlib import Path
import re
import sys
import uuid
from typing import Any

_BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, Request, UploadFile, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.agent import (
    ModelStatus,
    WorkflowNotFoundError,
    assess_paperwork,
    assess_paperwork_deterministic,
    get_model_status,
)
from app.schemas import DocumentUploadResponse, ReadinessAssessment
from app.tools.documents import (
    DOCUMENTS_DIR,
    SUPPORTED_EXTENSIONS,
    _get_file_metadata,
    _make_document_id,
    list_documents,
)
from app.tools.requirements import WORKFLOWS_DIR



_BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(_BACKEND_DIR / ".env")
load_dotenv()
logger = logging.getLogger("app.api")

app = FastAPI(
    title="Paperwork Agent API",
    description="Backend API for administrative document verification and paperwork readiness assessment.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ---------------------------------------------------------------------------
# CORS Configuration for local frontend development
# ---------------------------------------------------------------------------
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request and Response Models
# ---------------------------------------------------------------------------
class AssessRequest(BaseModel):
    """Request model for paperwork readiness assessment."""

    user_goal: str = Field(
        ...,
        description="Natural language paperwork goal (e.g. 'I want to complete the example application.')",
        examples=["I want to complete the example application."],
    )


class WorkflowSummary(BaseModel):
    """Clean summary of a registered paperwork workflow definition."""

    workflow_id: str
    workflow_name: str
    description: str
    requirements_count: int = 0


class DocumentUploadResponse(BaseModel):
    """Response model for uploaded document."""

    document_id: str = Field(description="Stable identifier for the stored document")
    filename: str = Field(description="Sanitized stored filename")
    original_filename: str = Field(description="Original uploaded filename")
    file_type: str = Field(description="File extension")
    size_bytes: int = Field(description="Stored file size in bytes")
    modified_at: str = Field(description="Creation or modification timestamp")
    message: str = Field(default="File uploaded successfully", description="Status message")


class PreparePackageRequest(BaseModel):
    """Request model for preparing an approved paperwork package."""

    assessment: ReadinessAssessment
    applicant_name: str | None = None
    notes: str | None = None


class PreparedPackageResponse(BaseModel):
    """Response model for a prepared paperwork package."""

    package_id: str
    approved: bool = True
    workflow_id: str
    workflow_name: str
    ready: bool
    package: dict[str, Any]
    markdown_summary: str


# ---------------------------------------------------------------------------
# Error Handlers
# ---------------------------------------------------------------------------
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Return HTTP 400 for invalid/malformed request bodies rather than 422."""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": "Invalid request body or missing required fields.", "errors": exc.errors()},
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/api/health", summary="Health Check")
async def health_check() -> dict[str, str]:
    """Check API server health status.

    Does not require any LLM API key or external service dependencies.
    """
    return {"status": "ok"}


@app.get("/api/workflows", response_model=list[WorkflowSummary], summary="List Workflows")
async def get_workflows() -> list[WorkflowSummary]:
    """Return available workflow definitions from the workflow registry.

    Reads registered workflow definitions from data/workflows/ without duplicating data.
    """
    if not WORKFLOWS_DIR.exists():
        return []

    workflows: list[WorkflowSummary] = []
    for path in sorted(WORKFLOWS_DIR.glob("*.json")):
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and "workflow_id" in data:
                workflows.append(
                    WorkflowSummary(
                        workflow_id=data["workflow_id"],
                        workflow_name=data.get("workflow_name", data["workflow_id"]),
                        description=data.get("description", ""),
                        requirements_count=len(data.get("requirements", [])),
                    )
                )
        except Exception as e:
            logger.warning(f"Could not read workflow definition from {path.name}: {e}")
            continue

    return workflows


class GenerateWorkflowRequest(BaseModel):
    """Request model for on-the-fly workflow schema generation."""
    user_goal: str = Field(..., description="Target paperwork goal or document checklist name")


@app.post("/api/workflows/generate", summary="Generate Workflow Schema on Demand")
async def generate_workflow_endpoint(request: GenerateWorkflowRequest) -> dict[str, Any]:
    """Generate and register a structured workflow schema dynamically for any goal."""
    from app.workflow_generator import generate_and_register_workflow

    goal = request.user_goal.strip()
    if not goal:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user_goal must not be empty.",
        )

    try:
        wf = generate_and_register_workflow(goal)
        return {
            "status": "success",
            "workflow": wf,
            "message": f"Successfully registered workflow schema for '{wf.get('workflow_name')}'",
        }
    except Exception as e:
        logger.exception(f"Failed to generate workflow: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate workflow: {str(e)}",
        )



async def _process_and_save_upload(file: UploadFile) -> DocumentUploadResponse:
    """Validate, sanitize, and store an uploaded document in the local document store."""
    if not file or not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file provided or filename is empty.",
        )

    # Sanitize and strip path traversal attempts
    raw_filename = os.path.basename(file.filename.strip())
    if not raw_filename or raw_filename in {".", ".."}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or unsafe filename provided.",
        )

    # Check file extension against supported types
    ext = Path(raw_filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        supported_str = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type '{ext}'. Supported formats: {supported_str}",
        )

    # Size limit validation
    max_mb = int(os.environ.get("MAX_UPLOAD_SIZE_MB", "10"))
    max_bytes = max_mb * 1024 * 1024

    try:
        content = await file.read()
    except Exception as e:
        logger.error(f"Failed to read uploaded file stream: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to read file content.",
        )

    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    if len(content) > max_bytes:
        raise HTTPException(
            status_code=getattr(status, "HTTP_413_CONTENT_TOO_LARGE", 413),
            detail=f"File exceeds maximum allowed size of {max_mb} MB.",
        )


    # Generate sanitized filename
    stem = Path(raw_filename).stem
    clean_stem = re.sub(r"[^\w\s\.-]", "", stem).strip()
    clean_stem = re.sub(r"\s+", "_", clean_stem)
    if not clean_stem:
        clean_stem = f"doc_{hashlib.md5(content).hexdigest()[:8]}"

    target_filename = f"{clean_stem}{ext}"

    # Ensure document storage directory exists
    DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
    target_path = DOCUMENTS_DIR / target_filename

    # Prevent collision if different content already exists with identical name
    if target_path.exists():
        try:
            existing_content = target_path.read_bytes()
            if existing_content != content:
                content_hash = hashlib.md5(content).hexdigest()[:6]
                target_filename = f"{clean_stem}_{content_hash}{ext}"
                target_path = DOCUMENTS_DIR / target_filename
        except Exception:
            pass

    try:
        target_path.write_bytes(content)
    except Exception as e:
        logger.exception(f"Failed to save document to local storage: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to write document to local storage.",
        )

    doc_id = _make_document_id(target_filename)
    meta = _get_file_metadata(target_path)
    logger.info(
        f"Uploaded document '{target_filename}' (doc_id: {doc_id}, size: {meta['size_bytes']} bytes)"
    )

    return DocumentUploadResponse(
        document_id=doc_id,
        filename=target_filename,
        original_filename=raw_filename,
        file_type=ext.lstrip("."),
        size_bytes=meta["size_bytes"],
        modified_at=meta["modified_at"],
        message="Document uploaded and indexed successfully.",
    )


@app.post(
    "/api/documents/upload",
    response_model=DocumentUploadResponse,
    summary="Upload Document",
    responses={
        400: {"description": "Invalid filename or empty file"},
        413: {"description": "File exceeds maximum size limit"},
        415: {"description": "Unsupported file format"},
        500: {"description": "Storage write failure"},
    },
)
async def upload_document(file: UploadFile = File(...)) -> DocumentUploadResponse:
    """Upload a supported document to the controlled local document storage.

    Validates file format, enforces size limits, safely sanitizes filenames,
    and indexes the document so it is immediately discoverable by all document
    and verification tools.
    """
    return await _process_and_save_upload(file)


@app.post(
    "/api/documents",
    response_model=DocumentUploadResponse,
    summary="Upload Document (Alias)",
    include_in_schema=False,
)
async def upload_document_alias(file: UploadFile = File(...)) -> DocumentUploadResponse:
    """Alias for /api/documents/upload."""
    return await _process_and_save_upload(file)


@app.delete(
    "/api/documents/{document_id}",
    summary="Delete Document",
    responses={
        404: {"description": "Document not found"},
        500: {"description": "Failed to delete document"},
    },
)
async def delete_document(document_id: str) -> dict[str, Any]:
    """Delete a document from local storage by its document_id."""
    if not DOCUMENTS_DIR.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Documents storage directory not found.",
        )

    target_path = None
    for path in DOCUMENTS_DIR.iterdir():
        if path.is_file() and _make_document_id(path.name) == document_id:
            target_path = path
            break

    if target_path is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{document_id}' was not found.",
        )

    try:
        filename = target_path.name
        target_path.unlink()
        logger.info(f"Deleted document '{filename}' (doc_id: {document_id})")
        return {
            "status": "deleted",
            "document_id": document_id,
            "filename": filename,
            "message": "Document deleted successfully.",
        }
    except Exception as e:
        logger.exception(f"Failed to delete document {document_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete document from storage.",
        )


@app.get("/api/documents", summary="List Documents")
async def get_documents() -> dict[str, Any]:
    """Return user documents currently available in the document store.

    Reuses the existing list_documents tool implementation without duplication.
    """
    try:
        raw_result = list_documents._tool_func()
        return json.loads(raw_result)
    except Exception as e:
        logger.exception(f"Error reading documents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve available documents.",
        )



@app.post(
    "/api/assess",
    response_model=ReadinessAssessment,
    summary="Assess Paperwork Readiness",
    responses={
        400: {"description": "Invalid or empty user_goal"},
        404: {"description": "Workflow not found for the specified goal"},
        500: {"description": "Internal assessment processing error"},
    },
)
async def assess(request: AssessRequest) -> ReadinessAssessment:
    """Assess user documents against a target paperwork workflow.

    Accepts a natural-language user goal, discovers the matching workflow, gathers
    evidence with provenance from local documents, runs authoritative verification,
    and returns a validated ReadinessAssessment.

    If an LLM API key (OPENAI_API_KEY or ANTHROPIC_API_KEY) is configured, the live
    Strands Agent handles orchestration. Otherwise, the safe deterministic pipeline
    is executed without fabricating LLM calls.
    """
    # Validate non-empty and non-whitespace user_goal
    cleaned_goal = request.user_goal.strip()
    if not cleaned_goal:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user_goal must not be empty or whitespace only.",
        )

    model_status, status_msg = get_model_status()

    try:
        if model_status == ModelStatus.LIVE_READY:
            provider = os.environ.get("MODEL_PROVIDER", "openai").lower()
            logger.info(f"Executing LIVE STRANDS AGENT assessment with {provider}...")
            try:
                return assess_paperwork(cleaned_goal)
            except Exception as e:
                logger.error(
                    f"Live agent execution failed: {e}. Not converting to deterministic output."
                )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Live agent execution failed: {e}",
                )
        elif model_status == ModelStatus.NO_CREDENTIALS:
            logger.info(
                f"Executing deterministic assessment pipeline (reason: {model_status.value} - {status_msg})..."
            )
            return assess_paperwork_deterministic(cleaned_goal)
        else:
            # INVALID_PROVIDER
            logger.error(f"Invalid model configuration: {status_msg}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Invalid model configuration: {status_msg}",
            )

    except HTTPException:
        raise
    except WorkflowNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(f"Unexpected assessment error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while assessing paperwork.",
        )

@app.post(
    "/api/package/prepare",
    response_model=PreparedPackageResponse,
    summary="Prepare Approved Paperwork Package",
    responses={
        400: {"description": "Invalid assessment payload"},
    },
)
async def prepare_package(request: PreparePackageRequest) -> PreparedPackageResponse:
    """Prepare an approved application package and Markdown summary from an existing ReadinessAssessment.

    Operates strictly on the already-produced ReadinessAssessment. Does NOT re-invoke the
    LLM or Strands agent. The human approval authorizes work product preparation,
    not external submission.
    """
    assessment = request.assessment
    package_id = f"pkg-{uuid.uuid4().hex[:8]}"
    created_at = datetime.now(timezone.utc).isoformat()

    all_checks = (
        assessment.satisfied_requirements
        + assessment.missing_requirements
        + assessment.conflicts
        + assessment.uncertainties
    )

    # Determine applicant name from request or extracted facts
    applicant_name = request.applicant_name
    if not applicant_name:
        for check in all_checks:
            for fact in check.evidence:
                if fact.field.lower() in ("full_name", "name", "applicant_name") and fact.value:
                    applicant_name = str(fact.value)
                    break
            if applicant_name:
                break
    if not applicant_name:
        applicant_name = "Applicant"

    # Collect unique verified facts across requirements
    verified_facts: list[dict[str, Any]] = []
    seen_fact_keys: set[tuple[str, str, str | None]] = set()
    for check in all_checks:
        for fact in check.evidence:
            key = (fact.source_document, fact.field, fact.value)
            if key not in seen_fact_keys:
                seen_fact_keys.add(key)
                verified_facts.append({
                    "field": fact.field,
                    "value": fact.value,
                    "source_document": fact.source_document,
                    "source_page": fact.source_page,
                    "confidence": fact.confidence,
                    "evidence_snippet": fact.evidence_snippet,
                })

    # Collect conflicts
    conflict_items: list[dict[str, Any]] = []
    for check in assessment.conflicts:
        for conf in check.conflicts:
            conflict_items.append({
                "field": conf.field,
                "requirement_name": check.requirement_name,
                "values": conf.values,
                "notes": check.notes,
            })

    package_data: dict[str, Any] = {
        "package_id": package_id,
        "workflow_id": assessment.workflow_id,
        "workflow_name": assessment.workflow_name,
        "applicant_name": applicant_name,
        "created_at": created_at,
        "ready": assessment.ready,
        "completion_percentage": assessment.completion_percentage,
        "status": "APPROVED_FOR_PREPARATION" if assessment.ready else "PREPARED_WITH_FLAGGED_GAPS",
        "human_review": {
            "approved": True,
            "reviewed_at": created_at,
            "notes": request.notes or "Approved for preparation by human reviewer.",
        },
        "requirements_summary": {
            "satisfied": [c.model_dump() for c in assessment.satisfied_requirements],
            "missing": [c.model_dump() for c in assessment.missing_requirements],
            "conflicts": [c.model_dump() for c in assessment.conflicts],
            "uncertainties": [c.model_dump() for c in assessment.uncertainties],
        },
        "verified_facts": verified_facts,
        "conflicts": conflict_items,
        "recommended_next_actions": assessment.recommended_next_actions,
    }

    # Generate authoritative, clean Markdown summary
    status_text = "READY FOR SUBMISSION" if assessment.ready else "ACTION REQUIRED (INCOMPLETE / CONFLICTING EVIDENCE)"
    md_lines = [
        f"# Application Readiness Package: {assessment.workflow_name}",
        "",
        f"- **Package ID:** `{package_id}`",
        f"- **Workflow ID:** `{assessment.workflow_id}`",
        f"- **Applicant:** {applicant_name}",
        f"- **Generated At:** {created_at}",
        f"- **Readiness Status:** {status_text}",
        f"- **Completion:** {assessment.completion_percentage}%",
        "",
        "## 1. Human Review Authorization",
        "- **Review Decision:** Approved for work product preparation",
        f"- **Reviewer Notes:** {request.notes or 'Approved for preparation by human reviewer.'}",
        "",
        "## 2. Requirement Verification Checklist",
    ]

    for check in assessment.satisfied_requirements:
        md_lines.append(f"### ✅ SATISFIED: {check.requirement_name}")
        md_lines.append(f"- **Requirement ID:** `{check.requirement_id}`")
        if check.evidence:
            md_lines.append("- **Supporting Evidence:**")
            for ev in check.evidence:
                md_lines.append(f"  - `{ev.source_document}`: {ev.field} = *\"{ev.value}\"* (confidence: {ev.confidence})")
        md_lines.append("")

    for check in assessment.missing_requirements:
        md_lines.append(f"### ❌ MISSING: {check.requirement_name}")
        md_lines.append(f"- **Requirement ID:** `{check.requirement_id}`")
        md_lines.append(f"- **Guidance:** {check.notes or 'No supporting document found.'}")
        md_lines.append("")

    for check in assessment.conflicts:
        md_lines.append(f"### ⚠️ CONFLICT: {check.requirement_name}")
        md_lines.append(f"- **Requirement ID:** `{check.requirement_id}`")
        md_lines.append(f"- **Details:** {check.notes or 'Conflicting values found across documents.'}")
        for conf in check.conflicts:
            val_strs = [f"{v.get('value')} ({v.get('source_document')})" for v in conf.values]
            md_lines.append(f"  - **{conf.field}**: {', '.join(val_strs)}")
        md_lines.append("")

    for check in assessment.uncertainties:
        md_lines.append(f"### ❓ UNCERTAIN: {check.requirement_name}")
        md_lines.append(f"- **Requirement ID:** `{check.requirement_id}`")
        md_lines.append(f"- **Details:** {check.notes or 'Confidence is low or verification uncertain.'}")
        md_lines.append("")

    md_lines.append("## 3. Verified Facts & Document Provenance")
    if verified_facts:
        for f in verified_facts:
            md_lines.append(f"- **{f['field']}**: `{f['value']}` *(Source: `{f['source_document']}`, Confidence: {f['confidence']})*")
    else:
        md_lines.append("- *No verified facts extracted.*")

    md_lines.append("")
    md_lines.append("## 4. Flagged Conflicts & Discrepancies")
    if conflict_items:
        for conf in conflict_items:
            val_strs = [f"'{v.get('value')}' in `{v.get('source_document')}`" for v in conf.get("values", [])]
            md_lines.append(f"- ⚠️ **{conf['field']} Discrepancy**: {', '.join(val_strs)}")
            if conf.get("notes"):
                md_lines.append(f"  - {conf['notes']}")
    else:
        md_lines.append("- *No document conflicts detected.*")

    if assessment.recommended_next_actions:
        md_lines.append("")
        md_lines.append("## 5. Recommended Next Actions")
        for act in assessment.recommended_next_actions:
            md_lines.append(f"- {act}")

    md_lines.append("")
    markdown_summary = "\n".join(md_lines)

    return PreparedPackageResponse(
        package_id=package_id,
        approved=True,
        workflow_id=assessment.workflow_id,
        workflow_name=assessment.workflow_name,
        ready=assessment.ready,
        package=package_data,
        markdown_summary=markdown_summary,
    )

