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


class TestDocumentUploadEndpoints:
    """Tests for POST /api/documents/upload and DELETE /api/documents/{document_id}."""

    def test_upload_valid_text_document(self):
        filename = "test_birth_certificate.txt"
        content = b"Full Name: Arion Dutta\nDate of Birth: 12 March 2000\nPlace of Birth: Kolkata\n"
        
        try:
            response = client.post(
                "/api/documents/upload",
                files={"file": (filename, content, "text/plain")},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["filename"] == filename
            assert data["original_filename"] == filename
            assert data["file_type"] == "txt"
            assert data["size_bytes"] == len(content)
            assert "document_id" in data
            doc_id = data["document_id"]

            # Verify it appears in GET /api/documents
            list_res = client.get("/api/documents")
            assert list_res.status_code == 200
            docs = list_res.json()["documents"]
            found = next((d for d in docs if d["document_id"] == doc_id), None)
            assert found is not None
            assert found["filename"] == filename

        finally:
            # Clean up
            client.delete(f"/api/documents/{doc_id}")

    def test_upload_unsupported_extension_returns_415(self):
        response = client.post(
            "/api/documents/upload",
            files={"file": ("malicious_script.exe", b"binary content", "application/octet-stream")},
        )
        assert response.status_code == 415
        assert "Unsupported file type" in response.json()["detail"]

    def test_upload_empty_file_returns_400(self):
        response = client.post(
            "/api/documents/upload",
            files={"file": ("empty_file.txt", b"", "text/plain")},
        )
        assert response.status_code == 400
        assert "empty" in response.json()["detail"].lower()

    def test_upload_oversized_file_returns_413(self):
        # Set max upload size to 1MB for testing
        with patch.dict(os.environ, {"MAX_UPLOAD_SIZE_MB": "1"}, clear=False):
            large_content = b"A" * (2 * 1024 * 1024)  # 2MB
            response = client.post(
                "/api/documents/upload",
                files={"file": ("large_doc.txt", large_content, "text/plain")},
            )
            assert response.status_code == 413
            assert "exceeds maximum allowed size" in response.json()["detail"]

    def test_upload_path_traversal_is_sanitized(self):
        traversal_name = "../../etc/passwd.txt"
        content = b"Full Name: Test User\n"
        doc_id = None
        try:
            response = client.post(
                "/api/documents/upload",
                files={"file": (traversal_name, content, "text/plain")},
            )
            assert response.status_code == 200
            data = response.json()
            # Stored filename must not contain directory traversal slashes
            assert "/" not in data["filename"]
            assert "\\" not in data["filename"]
            assert ".." not in data["filename"]
            doc_id = data["document_id"]
        finally:
            if doc_id:
                client.delete(f"/api/documents/{doc_id}")

    def test_uploaded_document_integrates_with_pipeline_tools(self):
        """Verify uploaded document is readable, searchable, and fact-extractable."""
        from app.tools.documents import read_document, search_documents, extract_document_facts
        import json

        filename = "test_pipeline_doc.txt"
        content = b"Full Name: Jane Doe\nDate of Birth: 15 August 1995\nNationality: Canadian\n"
        doc_id = None

        try:
            res = client.post(
                "/api/documents/upload",
                files={"file": (filename, content, "text/plain")},
            )
            assert res.status_code == 200
            doc_id = res.json()["document_id"]

            # 1. read_document tool
            read_res = json.loads(read_document._tool_func(document_id=doc_id))
            assert "content" in read_res
            assert "Jane Doe" in read_res["content"]

            # 2. search_documents tool
            search_res = json.loads(search_documents._tool_func(query="Jane Doe Canadian"))
            assert len(search_res["results"]) > 0
            matching_hit = next((r for r in search_res["results"] if r["document_id"] == doc_id), None)
            assert matching_hit is not None

            # 3. extract_document_facts tool
            facts_res = json.loads(extract_document_facts._tool_func(
                document_id=doc_id,
                requested_fields="full_name,date_of_birth,nationality",
            ))
            extracted = {f["field"]: f["value"] for f in facts_res["extracted_facts"]}
            assert extracted.get("full_name") == "Jane Doe"
            assert extracted.get("date_of_birth") == "15 August 1995"
            assert extracted.get("nationality") == "Canadian"

        finally:
            if doc_id:
                client.delete(f"/api/documents/{doc_id}")

    def test_delete_nonexistent_document_returns_404(self):
        response = client.delete("/api/documents/nonexistent_id_12345")
        assert response.status_code == 404

