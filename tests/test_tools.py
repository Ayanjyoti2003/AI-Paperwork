"""Tests for the Paperwork Agent deterministic functionality.

Run with: python -m pytest tests/ -v
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.tools.documents import (
    DOCUMENTS_DIR,
    _extract_single_fact,
    _make_document_id,
    _read_text_file,
)


class TestDocumentDiscovery:
    """Tests for document listing and discovery."""

    def test_documents_directory_exists(self):
        assert DOCUMENTS_DIR.exists(), f"Documents dir not found: {DOCUMENTS_DIR}"

    def test_demo_documents_present(self):
        files = [f.name for f in DOCUMENTS_DIR.iterdir() if f.is_file()]
        assert "identity.txt" in files
        assert "address_proof.txt" in files
        assert "certificate.txt" in files

    def test_list_documents_returns_valid_json(self):
        from app.tools.documents import list_documents
        # Call the underlying function directly (Strands @tool wraps it)
        # We need to call the actual function, not the tool wrapper
        result = list_documents._tool_func()
        data = json.loads(result)
        assert "documents" in data
        assert data["count"] >= 3

    def test_document_ids_are_stable(self):
        id1 = _make_document_id("identity.txt")
        id2 = _make_document_id("identity.txt")
        assert id1 == id2

    def test_document_ids_are_unique(self):
        ids = {_make_document_id(f.name) for f in DOCUMENTS_DIR.iterdir() if f.is_file()}
        files = [f.name for f in DOCUMENTS_DIR.iterdir() if f.is_file()]
        assert len(ids) == len(files), "Document IDs should be unique"


class TestDocumentSearch:
    """Tests for document search functionality."""

    def test_search_finds_identity(self):
        from app.tools.documents import search_documents

        result = search_documents._tool_func(query="date of birth identity")
        data = json.loads(result)
        assert "results" in data
        assert len(data["results"]) > 0
        filenames = [r["filename"] for r in data["results"]]
        assert "identity.txt" in filenames

    def test_search_finds_address(self):
        from app.tools.documents import search_documents

        result = search_documents._tool_func(query="address proof utility bill")
        data = json.loads(result)
        filenames = [r["filename"] for r in data["results"]]
        assert "address_proof.txt" in filenames

    def test_search_returns_relevance_scores(self):
        from app.tools.documents import search_documents

        result = search_documents._tool_func(query="name")
        data = json.loads(result)
        for r in data["results"]:
            assert "relevance_score" in r
            assert 0.0 <= r["relevance_score"] <= 1.0

    def test_search_no_results(self):
        from app.tools.documents import search_documents

        result = search_documents._tool_func(query="xyzzy_nonexistent_term_12345")
        data = json.loads(result)
        assert data["results"] == []


class TestDocumentReading:
    """Tests for reading document contents."""

    def test_read_existing_document(self):
        from app.tools.documents import read_document

        doc_id = _make_document_id("identity.txt")
        result = read_document._tool_func(document_id=doc_id)
        data = json.loads(result)
        assert "content" in data
        assert "Jane Alexandra Doe" in data["content"]

    def test_read_nonexistent_document(self):
        from app.tools.documents import read_document

        result = read_document._tool_func(document_id="nonexistent_id")
        data = json.loads(result)
        assert "error" in data


class TestFactExtraction:
    """Tests for extracting facts from documents."""

    def test_extract_name_from_identity(self):
        content = _read_text_file(DOCUMENTS_DIR / "identity.txt")
        doc_id = _make_document_id("identity.txt")
        fact = _extract_single_fact("full_name", content, doc_id, "identity.txt")
        assert fact["value"] is not None
        assert "Jane" in fact["value"]
        assert fact["confidence"] == "high"

    def test_extract_dob_from_identity(self):
        content = _read_text_file(DOCUMENTS_DIR / "identity.txt")
        doc_id = _make_document_id("identity.txt")
        fact = _extract_single_fact("date_of_birth", content, doc_id, "identity.txt")
        assert fact["value"] is not None
        assert "1995-03-15" in fact["value"]

    def test_extract_dob_from_certificate(self):
        content = _read_text_file(DOCUMENTS_DIR / "certificate.txt")
        doc_id = _make_document_id("certificate.txt")
        fact = _extract_single_fact("date_of_birth", content, doc_id, "certificate.txt")
        assert fact["value"] is not None
        assert "1995-03-16" in fact["value"]

    def test_extract_missing_field(self):
        content = _read_text_file(DOCUMENTS_DIR / "identity.txt")
        doc_id = _make_document_id("identity.txt")
        fact = _extract_single_fact("employer", content, doc_id, "identity.txt")
        assert fact["confidence"] in ("not_found", "low")

    def test_provenance_included(self):
        content = _read_text_file(DOCUMENTS_DIR / "identity.txt")
        doc_id = _make_document_id("identity.txt")
        fact = _extract_single_fact("full_name", content, doc_id, "identity.txt")
        assert fact["source_document"] == doc_id
        assert fact["evidence_snippet"] is not None


class TestRequirementLoading:
    """Tests for loading workflow requirements."""

    def test_load_example_workflow(self):
        from app.tools.requirements import get_workflow_requirements

        result = get_workflow_requirements._tool_func(workflow_id="example_application")
        data = json.loads(result)
        assert "requirements" in data
        assert len(data["requirements"]) >= 4

    def test_load_nonexistent_workflow(self):
        from app.tools.requirements import get_workflow_requirements

        result = get_workflow_requirements._tool_func(workflow_id="nonexistent_workflow")
        data = json.loads(result)
        assert "error" in data

    def test_workflow_has_required_fields(self):
        from app.tools.requirements import get_workflow_requirements

        result = get_workflow_requirements._tool_func(workflow_id="example_application")
        data = json.loads(result)
        for req in data["requirements"]:
            assert "id" in req
            assert "name" in req
            assert "required" in req
            assert "relevant_fields" in req


class TestConflictDetection:
    """Tests for the verification tool's conflict detection."""

    def test_conflict_detected_on_dob(self):
        from app.tools.verification import verify_requirements

        # Simulate evidence with conflicting DOB values
        evidence = [
            {
                "field": "date_of_birth",
                "value": "1995-03-15",
                "source_document": "doc_identity",
                "confidence": "high",
                "evidence_snippet": "Date of Birth: 1995-03-15",
            },
            {
                "field": "date_of_birth",
                "value": "1995-03-16",
                "source_document": "doc_certificate",
                "confidence": "high",
                "evidence_snippet": "Date of Birth: 1995-03-16",
            },
            {
                "field": "full_name",
                "value": "Jane Alexandra Doe",
                "source_document": "doc_identity",
                "confidence": "high",
                "evidence_snippet": "Full Name: Jane Alexandra Doe",
            },
            {
                "field": "nationality",
                "value": "Freedonian",
                "source_document": "doc_identity",
                "confidence": "high",
                "evidence_snippet": "Nationality: Freedonian",
            },
            {
                "field": "id_number",
                "value": "NIC-2024-78901",
                "source_document": "doc_identity",
                "confidence": "high",
                "evidence_snippet": "Card Number: NIC-2024-78901",
            },
        ]

        result = verify_requirements._tool_func(
            workflow_id="example_application",
            evidence_json=json.dumps(evidence),
        )
        data = json.loads(result)

        # DOB requirement should show conflict
        dob_check = next(
            (c for c in data.get("conflicts", []) if c["requirement_id"] == "req_dob"),
            None,
        )
        assert dob_check is not None, "DOB conflict should be detected"
        assert dob_check["status"] == "conflict"
        assert len(dob_check["conflicts"]) > 0

    def test_missing_requirement_detected(self):
        from app.tools.verification import verify_requirements

        # Evidence that does NOT include employment information
        evidence = [
            {
                "field": "full_name",
                "value": "Jane Alexandra Doe",
                "source_document": "doc_identity",
                "confidence": "high",
                "evidence_snippet": "Full Name: Jane Alexandra Doe",
            },
        ]

        result = verify_requirements._tool_func(
            workflow_id="example_application",
            evidence_json=json.dumps(evidence),
        )
        data = json.loads(result)

        # Employment requirement should be missing
        emp_check = next(
            (c for c in data.get("missing_requirements", []) if c["requirement_id"] == "req_employment"),
            None,
        )
        assert emp_check is not None, "Employment requirement should be missing"
        assert emp_check["status"] == "missing"

    def test_satisfied_requirement(self):
        from app.tools.verification import verify_requirements

        evidence = [
            {
                "field": "full_name",
                "value": "Jane Alexandra Doe",
                "source_document": "doc_identity",
                "confidence": "high",
                "evidence_snippet": "Full Name: Jane Alexandra Doe",
            },
            {
                "field": "date_of_birth",
                "value": "1995-03-15",
                "source_document": "doc_identity",
                "confidence": "high",
                "evidence_snippet": "DOB: 1995-03-15",
            },
            {
                "field": "nationality",
                "value": "Freedonian",
                "source_document": "doc_identity",
                "confidence": "high",
                "evidence_snippet": "Nationality: Freedonian",
            },
            {
                "field": "id_number",
                "value": "NIC-2024-78901",
                "source_document": "doc_identity",
                "confidence": "high",
                "evidence_snippet": "Card Number: NIC-2024-78901",
            },
        ]

        result = verify_requirements._tool_func(
            workflow_id="example_application",
            evidence_json=json.dumps(evidence),
        )
        data = json.loads(result)

        # Identity requirement should be satisfied (single DOB value = no conflict)
        identity_check = next(
            (c for c in data.get("satisfied_requirements", []) if c["requirement_id"] == "req_identity"),
            None,
        )
        assert identity_check is not None, "Identity requirement should be satisfied"
        assert identity_check["status"] == "satisfied"

    def test_assessment_not_ready_when_missing(self):
        from app.tools.verification import verify_requirements

        evidence = [
            {
                "field": "full_name",
                "value": "Jane",
                "source_document": "doc1",
                "confidence": "high",
                "evidence_snippet": "Name: Jane",
            },
        ]
        result = verify_requirements._tool_func(
            workflow_id="example_application",
            evidence_json=json.dumps(evidence),
        )
        data = json.loads(result)
        assert data["ready"] is False
        assert data["completion_percentage"] < 100
