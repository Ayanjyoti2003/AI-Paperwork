"""FastAPI Backend API Layer for the Paperwork Agent.

Provides endpoints for health check, workflow discovery, document inspection,
and paperwork readiness assessment. Compatible with local frontend development
via CORS and OpenAPI documentation.
"""

from __future__ import annotations

from datetime import datetime
import hashlib
import json
import logging
import os
from pathlib import Path
import re
import sys
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

    WorkflowNotFoundError,
    assess_paperwork,
    assess_paperwork_deterministic,
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
# Request Models
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

    # Check if a live model provider or local model is configured
    provider = os.environ.get("MODEL_PROVIDER", "openai").lower()
    if provider in {"ollama", "local"}:
        has_live_credentials = True
    elif provider == "groq":
        key = os.environ.get("GROQ_API_KEY", "")
        has_live_credentials = bool(key and not key.startswith("your-"))
    elif provider == "openrouter":
        key = os.environ.get("OPENROUTER_API_KEY", "")
        has_live_credentials = bool(key and not key.startswith("your-"))
    else:
        key = os.environ.get(f"{provider.upper()}_API_KEY", "")
        has_live_credentials = bool(key and not key.startswith("your-"))

    try:
        if has_live_credentials:
            try:
                logger.info(f"Executing live Strands agent assessment with {provider}...")

                return assess_paperwork(cleaned_goal)
            except Exception as e:
                logger.warning(
                    f"Live agent execution failed: {e}. Executing deterministic fallback."
                )
                return assess_paperwork_deterministic(cleaned_goal)
        else:
            # Deterministic assessment pipeline when no live LLM key is configured
            logger.info("Executing deterministic assessment pipeline (no API key set)...")
            return assess_paperwork_deterministic(cleaned_goal)

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
