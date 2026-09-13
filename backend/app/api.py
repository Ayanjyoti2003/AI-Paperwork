"""FastAPI Backend API Layer for the Paperwork Agent.

Provides endpoints for health check, workflow discovery, document inspection,
and paperwork readiness assessment. Compatible with local frontend development
via CORS and OpenAPI documentation.
"""

from __future__ import annotations

import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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
from app.schemas import ReadinessAssessment
from app.tools.documents import DOCUMENTS_DIR, SUPPORTED_EXTENSIONS, list_documents
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

    filename: str
    size_bytes: int
    message: str = "File uploaded successfully"


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
            logger.info("Executing LIVE STRANDS AGENT assessment...")
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
    "/api/documents/upload",
    response_model=DocumentUploadResponse,
    summary="Upload User Document",
    responses={
        400: {"description": "Invalid file, unsupported extension, or path traversal attempt"},
        500: {"description": "Failed to save uploaded file"},
    },
)
async def upload_document(file: UploadFile = File(...)) -> DocumentUploadResponse:
    """Safely upload a user document to the local document vault.

    Security & Safety guarantees:
    - Path traversal protection: extracts basename via Path(name).name and resolves against DOCUMENTS_DIR.
    - Supported extensions validation: (.txt, .md, .json, .pdf, .png, .jpg, .jpeg).
    - Accidental overwrite protection: generates collision-free suffix if file exists.
    - Files are strictly stored as static data and never executed.
    """
    raw_filename = file.filename or "upload.txt"
    filename_only = Path(raw_filename).name
    safe_filename = re.sub(r"[^a-zA-Z0-9_.-]", "_", filename_only)
    if not safe_filename or safe_filename.startswith("."):
        safe_filename = f"upload_{uuid.uuid4().hex[:6]}.txt"

    ext = Path(safe_filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file extension '{ext}'. Allowed extensions: {', '.join(sorted(SUPPORTED_EXTENSIONS))}",
        )

    target_dir = DOCUMENTS_DIR.resolve()
    target_dir.mkdir(parents=True, exist_ok=True)

    initial_target = (target_dir / safe_filename).resolve()
    if not initial_target.is_relative_to(target_dir):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename or path traversal detected.",
        )

    # Collision avoidance: protect existing demo and user documents from accidental overwrite
    target_path = initial_target
    if target_path.exists():
        stem = target_path.stem
        suffix = target_path.suffix
        unique_name = f"{stem}_{uuid.uuid4().hex[:6]}{suffix}"
        target_path = (target_dir / unique_name).resolve()

    try:
        content = await file.read()
        max_bytes = 10 * 1024 * 1024  # 10 MB limit
        if len(content) > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File size exceeds maximum allowed limit of 10MB.",
            )
        target_path.write_bytes(content)
        logger.info(f"Safely uploaded document: {target_path.name} ({len(content)} bytes)")
        return DocumentUploadResponse(
            filename=target_path.name,
            size_bytes=len(content),
            message="File uploaded successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to save uploaded file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while saving the uploaded document.",
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

