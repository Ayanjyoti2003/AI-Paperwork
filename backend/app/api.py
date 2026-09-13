"""FastAPI Backend API Layer for the Paperwork Agent.

Provides endpoints for health check, workflow discovery, document inspection,
and paperwork readiness assessment. Compatible with local frontend development
via CORS and OpenAPI documentation.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.agent import (
    WorkflowNotFoundError,
    assess_paperwork,
    assess_paperwork_deterministic,
)
from app.schemas import ReadinessAssessment
from app.tools.documents import list_documents
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

    # Check if a live model provider API key is set
    provider = os.environ.get("MODEL_PROVIDER", "openai").lower()
    key = os.environ.get(f"{provider.upper()}_API_KEY", "")
    has_live_credentials = bool(key and not key.startswith("your-"))

    try:
        if has_live_credentials:
            try:
                logger.info("Executing live Strands agent assessment...")
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
