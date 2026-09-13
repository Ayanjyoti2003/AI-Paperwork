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
from unittest.mock import patch

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
