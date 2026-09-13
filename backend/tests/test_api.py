"""Tests for the FastAPI Backend API Layer.

Verifies all endpoints using FastAPI TestClient:
- GET /api/health
- GET /api/workflows
- GET /api/documents
- POST /api/assess (valid goal, empty goal, whitespace goal, unknown workflow)
- Verification that API operates safely without an LLM API key.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import patch

# Ensure backend root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from fastapi.testclient import TestClient

from app.api import app

client = TestClient(app)


class TestHealthEndpoint:
    """Tests for GET /api/health."""

    def test_health_returns_200_and_ok(self):
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_health_works_without_llm_key(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "", "ANTHROPIC_API_KEY": ""}, clear=False):
            response = client.get("/api/health")
            assert response.status_code == 200
            assert response.json() == {"status": "ok"}


class TestWorkflowsEndpoint:
    """Tests for GET /api/workflows."""

    def test_get_workflows_returns_200_and_contains_example(self):
        response = client.get("/api/workflows")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

        example_wf = next((w for w in data if w["workflow_id"] == "example_application"), None)
        assert example_wf is not None
        assert "workflow_name" in example_wf
        assert "description" in example_wf
        assert example_wf["workflow_name"] == "Example Government Application"


class TestDocumentsEndpoint:
    """Tests for GET /api/documents."""

    def test_get_documents_returns_200_and_demo_files(self):
        response = client.get("/api/documents")
        assert response.status_code == 200
        data = response.json()
        assert "documents" in data
        assert data["count"] >= 3

        filenames = [d["filename"] for d in data["documents"]]
        assert "identity.txt" in filenames
        assert "address_proof.txt" in filenames
        assert "certificate.txt" in filenames


class TestAssessEndpoint:
    """Tests for POST /api/assess."""

    def test_assess_valid_goal_returns_200(self):
        payload = {"user_goal": "I want to complete the example application."}
        response = client.post("/api/assess", json=payload)
        assert response.status_code == 200
        data = response.json()

        # Verify all ReadinessAssessment fields
        expected_fields = [
            "workflow_id",
            "workflow_name",
            "ready",
            "completion_percentage",
            "satisfied_requirements",
            "missing_requirements",
            "conflicts",
            "uncertainties",
            "recommended_next_actions",
            "assessed_at",
        ]
        for field in expected_fields:
            assert field in data, f"Missing expected field: {field}"

        assert data["workflow_id"] == "example_application"
        assert data["ready"] is False
        assert isinstance(data["completion_percentage"], (int, float))
        assert len(data["satisfied_requirements"]) >= 1
        assert len(data["missing_requirements"]) >= 1
        assert len(data["conflicts"]) >= 1
        assert len(data["recommended_next_actions"]) >= 1

    def test_assess_empty_user_goal_returns_400(self):
        payload = {"user_goal": ""}
        response = client.post("/api/assess", json=payload)
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data

    def test_assess_whitespace_user_goal_returns_400(self):
        payload = {"user_goal": "   \n\t  "}
        response = client.post("/api/assess", json=payload)
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data

    def test_assess_missing_user_goal_field_returns_400(self):
        payload = {}
        response = client.post("/api/assess", json=payload)
        assert response.status_code == 400

    def test_assess_unknown_workflow_returns_404(self):
        payload = {"user_goal": "renew intergalactic starship captain permit"}
        response = client.post("/api/assess", json=payload)
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data

    def test_assess_works_without_llm_api_key(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "", "ANTHROPIC_API_KEY": ""}, clear=False):
            payload = {"user_goal": "I want to complete the example application."}
            response = client.post("/api/assess", json=payload)
            assert response.status_code == 200
            data = response.json()
            assert data["workflow_id"] == "example_application"
            assert "ready" in data

    def test_assess_with_live_credentials_fails_explicitly_on_live_error(self):
        """When live credentials are configured and live execution fails, API returns 500 without converting to deterministic output."""
        with patch.dict(
            os.environ,
            {"MODEL_PROVIDER": "openai", "OPENAI_API_KEY": "sk-test-live-key-configured"},
            clear=False,
        ):
            with patch("app.api.assess_paperwork", side_effect=RuntimeError("Simulated LLM network failure")):
                payload = {"user_goal": "I want to complete the example application."}
                response = client.post("/api/assess", json=payload)
                assert response.status_code == 500
                data = response.json()
                assert "detail" in data
                assert "Live agent execution failed" in data["detail"]


class TestDocumentUploadEndpoint:
    """Tests for POST /api/documents/upload."""

    def test_upload_valid_document(self):
        from app.tools.documents import DOCUMENTS_DIR

        test_filename = "test_upload_sample.txt"
        test_content = b"Sample upload content for testing."
        target_path = DOCUMENTS_DIR / test_filename
        if target_path.exists():
            target_path.unlink()

        try:
            response = client.post(
                "/api/documents/upload",
                files={"file": (test_filename, test_content, "text/plain")},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["filename"] == test_filename
            assert data["size_bytes"] == len(test_content)
            assert data["message"] == "File uploaded successfully"
            assert target_path.exists()
            assert target_path.read_bytes() == test_content
        finally:
            if target_path.exists():
                target_path.unlink()

    def test_upload_unsupported_extension_returns_400(self):
        response = client.post(
            "/api/documents/upload",
            files={"file": ("malicious_script.exe", b"binary content", "application/octet-stream")},
        )
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "Unsupported file extension" in data["detail"]

    def test_upload_path_traversal_sanitization(self):
        from app.tools.documents import DOCUMENTS_DIR

        traversal_name = "../../traversal_test.txt"
        test_content = b"Content meant to test path traversal safety."
        expected_safe_name = "traversal_test.txt"
        expected_path = DOCUMENTS_DIR / expected_safe_name

        try:
            response = client.post(
                "/api/documents/upload",
                files={"file": (traversal_name, test_content, "text/plain")},
            )
            assert response.status_code == 200
            data = response.json()
            # Must stay inside DOCUMENTS_DIR with safe filename
            assert expected_safe_name in data["filename"]
            # Path must exist inside DOCUMENTS_DIR, NOT at root or parent
            uploaded_file = DOCUMENTS_DIR / data["filename"]
            assert uploaded_file.exists()
            assert uploaded_file.is_relative_to(DOCUMENTS_DIR)
        finally:
            if expected_path.exists():
                expected_path.unlink()
            for p in DOCUMENTS_DIR.glob("*traversal_test*"):
                if p.is_file():
                    p.unlink()

    def test_upload_collision_avoidance_does_not_overwrite(self):
        from app.tools.documents import DOCUMENTS_DIR

        # identity.txt already exists as a demo file
        identity_path = DOCUMENTS_DIR / "identity.txt"
        original_content = identity_path.read_bytes()
        new_content = b"Attempt to overwrite identity.txt"

        created_path = None
        try:
            response = client.post(
                "/api/documents/upload",
                files={"file": ("identity.txt", new_content, "text/plain")},
            )
            assert response.status_code == 200
            data = response.json()
            uploaded_filename = data["filename"]

            # Filename must NOT overwrite original identity.txt
            assert uploaded_filename != "identity.txt"
            assert uploaded_filename.startswith("identity_")
            assert uploaded_filename.endswith(".txt")

            # Original file content must be completely untouched
            assert identity_path.read_bytes() == original_content

            created_path = DOCUMENTS_DIR / uploaded_filename
            assert created_path.exists()
            assert created_path.read_bytes() == new_content
        finally:
            if created_path and created_path.exists():
                created_path.unlink()


class TestPackagePrepareEndpoint:
    """Tests for POST /api/package/prepare."""

    def test_prepare_package_from_assessment_success(self):
        # 1. Get assessment via assess endpoint
        assess_resp = client.post(
            "/api/assess",
            json={"user_goal": "I want to complete the example application."},
        )
        assert assess_resp.status_code == 200
        assessment_data = assess_resp.json()

        # 2. Prepare package
        package_resp = client.post(
            "/api/package/prepare",
            json={
                "assessment": assessment_data,
                "applicant_name": "Arion Dutta",
                "notes": "Reviewed documents. Missing education cert noted.",
            },
        )
        assert package_resp.status_code == 200
        pkg = package_resp.json()

        assert pkg["approved"] is True
        assert pkg["package_id"].startswith("pkg-")
        assert pkg["workflow_id"] == "example_application"
        assert pkg["ready"] is False
        assert isinstance(pkg["package"], dict)
        assert pkg["package"]["applicant_name"] == "Arion Dutta"
        assert pkg["package"]["human_review"]["approved"] is True
        assert "Missing education cert noted" in pkg["package"]["human_review"]["notes"]

        # 3. Verify Markdown summary content
        md = pkg["markdown_summary"]
        assert "Application Readiness Package: Example Government Application" in md
        assert "Arion Dutta" in md
        assert "Human Review Authorization" in md
        assert "Requirement Verification Checklist" in md
        assert "Verified Facts & Document Provenance" in md
        assert "Flagged Conflicts & Discrepancies" in md

    def test_prepare_package_invalid_payload_returns_400(self):
        response = client.post(
            "/api/package/prepare",
            json={"invalid_field": 123},
        )
        assert response.status_code == 400

    def test_prepare_package_deterministic_no_llm_invocation(self):
        """Verify package preparation works completely offline without LLM keys."""
        assess_resp = client.post(
            "/api/assess",
            json={"user_goal": "I want to complete the example application."},
        )
        assessment_data = assess_resp.json()

        with patch.dict(os.environ, {"OPENAI_API_KEY": "", "ANTHROPIC_API_KEY": ""}, clear=False):
            with patch("app.api.assess_paperwork") as mock_agent:
                package_resp = client.post(
                    "/api/package/prepare",
                    json={"assessment": assessment_data},
                )
                assert package_resp.status_code == 200
                assert mock_agent.call_count == 0

