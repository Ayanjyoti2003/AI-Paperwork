"""Paperwork Agent - Phase 5A OCR & Scanned Document Tests.

Focused tests for:
1. Image upload succeeds (.png, .jpg, .jpeg).
2. Unsupported image/executable formats are rejected (.exe, .sh, .bmp).
3. OCR extraction returns normalized text.
4. OCR-derived text is searchable via search_documents().
5. Fact extraction can use OCR-derived text via extract_document_facts().
6. Provenance records extraction_method and actual confidence.
7. Native text documents still use native extraction.
8. Text PDFs do not unnecessarily require OCR.
9. Missing OCR dependency/provider produces an actionable error.
10. Textract provider configuration does not leak credentials or PII.
11. Existing deterministic demo remains unchanged.
"""

from __future__ import annotations

import io
import json
import logging
import os
import shutil
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.api import app
from app.ocr.base import (
    OCRConfigurationError,
    OCREngineUnavailableError,
    OCRProviderError,
    OCRResult,
)
from app.ocr.factory import get_ocr_provider
from app.ocr.local import LocalOCRProvider
from app.ocr.textract import TextractOCRProvider, check_aws_credentials
from app.tools.documents import (
    DOCUMENTS_DIR,
    _extract_single_fact,
    _make_document_id,
    extract_document_facts,
    get_document_extraction,
    list_documents,
    search_documents,
)

client = TestClient(app)


def _make_test_image_bytes(text: str = "Name: Demo Applicant\nDate of Birth: 15/03/1995") -> bytes:
    """Helper to generate a small in-memory PNG image."""
    img = Image.new("RGB", (600, 200), color="white")
    draw = ImageDraw.Draw(img)
    draw.text((20, 30), text, fill="black")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ---------------------------------------------------------------------------
# 1. Image Upload Tests
# ---------------------------------------------------------------------------
class TestImageUpload:
    """Test upload endpoint with image files."""

    def test_upload_png_succeeds(self):
        png_bytes = _make_test_image_bytes("GOVERNMENT ID DEMO")
        response = client.post(
            "/api/documents/upload",
            files={"file": ("test_upload_id.png", png_bytes, "image/png")},
        )
        assert response.status_code == 200
        data = response.json()
        assert "filename" in data
        assert data["filename"].endswith(".png")
        assert data["size_bytes"] == len(png_bytes)

        # Cleanup uploaded file
        uploaded_path = DOCUMENTS_DIR / data["filename"]
        if uploaded_path.exists():
            uploaded_path.unlink()

    def test_upload_jpeg_succeeds(self):
        img = Image.new("RGB", (300, 100), color="white")
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        jpg_bytes = buf.getvalue()

        response = client.post(
            "/api/documents/upload",
            files={"file": ("test_upload_photo.jpg", jpg_bytes, "image/jpeg")},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["filename"].endswith(".jpg")

        # Cleanup
        uploaded_path = DOCUMENTS_DIR / data["filename"]
        if uploaded_path.exists():
            uploaded_path.unlink()


# ---------------------------------------------------------------------------
# 2. Unsupported Formats Rejected
# ---------------------------------------------------------------------------
class TestUnsupportedFormatsRejected:
    """Verify security controls reject executables and unsupported image formats."""

    def test_upload_executable_rejected(self):
        response = client.post(
            "/api/documents/upload",
            files={"file": ("malicious.exe", b"MZ\x90\x00executable", "application/octet-stream")},
        )
        assert response.status_code == 400
        assert "Unsupported file extension" in response.json()["detail"]

    def test_upload_shell_script_rejected(self):
        response = client.post(
            "/api/documents/upload",
            files={"file": ("script.sh", b"#!/bin/bash\necho hello", "text/x-sh")},
        )
        assert response.status_code == 400
        assert "Unsupported file extension" in response.json()["detail"]

    def test_upload_unsupported_image_format_rejected(self):
        response = client.post(
            "/api/documents/upload",
            files={"file": ("image.bmp", b"BM\x00\x00bitmap", "image/bmp")},
        )
        assert response.status_code == 400
        assert "Unsupported file extension" in response.json()["detail"]


# ---------------------------------------------------------------------------
# 3. OCR Extraction Returns Normalized Text
# ---------------------------------------------------------------------------
class TestOCRExtraction:
    """Verify local OCR engine returns clean normalized text and metadata."""

    def test_ocr_extraction_on_demo_image(self):
        demo_image_path = backend_dir / "data" / "sample_documents" / "identity_scan.png"
        if not demo_image_path.exists():
            from scripts.make_demo_image import create_demo_identity_image
            create_demo_identity_image(demo_image_path)

        provider = LocalOCRProvider()
        result = provider.extract_text_from_file(demo_image_path)

        assert isinstance(result, OCRResult)
        assert result.extraction_method == "local_ocr"
        assert len(result.text) > 0
        assert "GOVERNMENT" in result.text.upper() or "DEMO" in result.text.upper()
        # Verify confidence is a float between 0 and 1
        assert result.confidence is not None
        assert 0.0 <= result.confidence <= 1.0


# ---------------------------------------------------------------------------
# 4. OCR-derived Text is Searchable
# ---------------------------------------------------------------------------
class TestOCRSearchability:
    """Verify search_documents() discovers OCR-extracted text."""

    def test_ocr_text_is_searchable(self, tmp_path):
        # Create a temp documents directory with a synthetic image
        temp_docs = tmp_path / "docs"
        temp_docs.mkdir()

        # Copy synthetic demo scan to temp docs
        sample_path = backend_dir / "data" / "sample_documents" / "identity_scan.png"
        if not sample_path.exists():
            from scripts.make_demo_image import create_demo_identity_image
            create_demo_identity_image(sample_path)

        shutil.copy(sample_path, temp_docs / "demo_scan.png")

        with patch("app.tools.documents.DOCUMENTS_DIR", temp_docs):
            search_json = search_documents._tool_func(query="Demo Applicant")
            data = json.loads(search_json)

            assert "results" in data
            assert len(data["results"]) >= 1
            hit = data["results"][0]
            assert hit["filename"] == "demo_scan.png"
            assert hit["relevance_score"] > 0.0


# ---------------------------------------------------------------------------
# 5. Fact Extraction from OCR
# ---------------------------------------------------------------------------
class TestFactExtractionFromOCR:
    """Verify extract_document_facts() extracts structured facts from OCR text."""

    def test_extract_facts_from_scanned_image(self, tmp_path):
        temp_docs = tmp_path / "docs"
        temp_docs.mkdir()

        sample_path = backend_dir / "data" / "sample_documents" / "identity_scan.png"
        if not sample_path.exists():
            from scripts.make_demo_image import create_demo_identity_image
            create_demo_identity_image(sample_path)

        shutil.copy(sample_path, temp_docs / "identity_scan.png")
        doc_id = _make_document_id("identity_scan.png")

        with patch("app.tools.documents.DOCUMENTS_DIR", temp_docs):
            facts_json = extract_document_facts._tool_func(
                document_id=doc_id,
                requested_fields="full_name,date_of_birth,address",
            )
            data = json.loads(facts_json)

            assert "extracted_facts" in data
            facts = {f["field"]: f for f in data["extracted_facts"]}

            # Verify key fields extracted
            assert "full_name" in facts
            assert facts["full_name"]["value"] is not None
            assert "date_of_birth" in facts
            assert facts["date_of_birth"]["value"] is not None
            assert "address" in facts
            assert facts["address"]["value"] is not None


# ---------------------------------------------------------------------------
# 6. Provenance Records Extraction Method
# ---------------------------------------------------------------------------
class TestProvenanceTracking:
    """Verify provenance metadata records extraction_method and confidence."""

    def test_ocr_provenance_method_and_confidence(self, tmp_path):
        temp_docs = tmp_path / "docs"
        temp_docs.mkdir()

        sample_path = backend_dir / "data" / "sample_documents" / "identity_scan.png"
        shutil.copy(sample_path, temp_docs / "scan.png")
        doc_id = _make_document_id("scan.png")

        with patch("app.tools.documents.DOCUMENTS_DIR", temp_docs):
            facts_json = extract_document_facts._tool_func(
                document_id=doc_id,
                requested_fields="date_of_birth",
            )
            data = json.loads(facts_json)
            fact = data["extracted_facts"][0]

            assert fact["extraction_method"] == "local_ocr"
            assert fact["source_page"] is not None
            # Confidence should be a real float from OCR, not invented
            assert isinstance(fact["confidence"], (float, int))
            assert 0.0 < fact["confidence"] <= 1.0


# ---------------------------------------------------------------------------
# 7. Native Text Extraction Still Used for Text Files
# ---------------------------------------------------------------------------
class TestNativeTextUnchanged:
    """Verify .txt, .md, .json continue using native text extraction."""

    def test_native_txt_provenance_is_native_text(self):
        doc_id = _make_document_id("identity.txt")
        facts_json = extract_document_facts._tool_func(
            document_id=doc_id,
            requested_fields="full_name",
        )
        data = json.loads(facts_json)
        fact = data["extracted_facts"][0]

        assert fact["extraction_method"] == "native_text"
        assert fact["confidence"] == "high"


# ---------------------------------------------------------------------------
# 8. Text PDFs Do Not Unnecessarily Require OCR
# ---------------------------------------------------------------------------
class TestTextPDFDoesNotRequireOCR:
    """Verify text-extractable PDFs use native text extraction without OCR."""

    def test_readable_pdf_uses_native_text(self, tmp_path):
        from fpdf import FPDF

        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", size=12)
        pdf.cell(200, 10, text="Full Name: Jane Alexandra Doe", ln=True)
        pdf.cell(200, 10, text="Date of Birth: 1995-03-15", ln=True)

        pdf_path = tmp_path / "native_doc.pdf"
        pdf.output(str(pdf_path))

        extraction = get_document_extraction(pdf_path)
        assert extraction.extraction_method == "native_text"
        assert "Jane Alexandra Doe" in extraction.content


# ---------------------------------------------------------------------------
# 9. Missing OCR Dependency Actionable Error
# ---------------------------------------------------------------------------
class TestMissingDependencyActionableError:
    """Verify missing engine raises actionable error."""

    def test_missing_rapidocr_raises_actionable_error(self):
        provider = LocalOCRProvider()
        with patch.dict(sys.modules, {"rapidocr_onnxruntime": None}):
            provider._engine_initialized = False
            with pytest.raises(OCREngineUnavailableError) as exc_info:
                provider._get_engine()
            assert "rapidocr-onnxruntime" in str(exc_info.value)
            assert "pip install" in str(exc_info.value)


# ---------------------------------------------------------------------------
# 10. Textract Provider Configuration & Privacy
# ---------------------------------------------------------------------------
class TestTextractProviderAndSecurity:
    """Test Textract provider with mocks and verify no secrets are leaked."""

    def test_textract_missing_credentials_raises_actionable_error(self):
        with patch.dict(os.environ, {"AWS_ACCESS_KEY_ID": "", "AWS_SECRET_ACCESS_KEY": ""}, clear=False):
            with patch("app.ocr.textract.check_aws_credentials", return_value=False):
                with pytest.raises(OCRConfigurationError) as exc_info:
                    provider = TextractOCRProvider()
                    provider.extract_text_from_image(b"fake_bytes")
                assert "no valid aws credentials" in str(exc_info.value).lower()

    def test_textract_explicit_failure_on_client_error(self):
        """If AWS credentials exist but call fails (e.g. AccessDenied), raises explicit OCRProviderError."""
        mock_client = MagicMock()
        mock_client.detect_document_text.side_effect = RuntimeError("AccessDeniedException: not authorized")

        provider = TextractOCRProvider(client=mock_client)
        with pytest.raises(OCRProviderError) as exc_info:
            provider.extract_text_from_image(b"fake_image_bytes")
        assert "Textract text detection failed" in str(exc_info.value)
        assert "AccessDeniedException" in str(exc_info.value)

    def test_textract_parses_lines_and_normalizes_confidence(self):
        mock_client = MagicMock()
        mock_client.detect_document_text.return_value = {
            "Blocks": [
                {"BlockType": "PAGE"},
                {"BlockType": "LINE", "Text": "GOVERNMENT ID — DEMO ONLY", "Confidence": 99.5, "Page": 1},
                {"BlockType": "LINE", "Text": "Name: Demo Applicant", "Confidence": 98.2, "Page": 1},
                {"BlockType": "LINE", "Text": "Date of Birth: 15/03/1995", "Confidence": 96.0, "Page": 1},
            ]
        }

        provider = TextractOCRProvider(client=mock_client)
        page = provider.extract_text_from_image(b"fake_image_bytes", page_number=1)

        assert "Demo Applicant" in page.text
        assert len(page.lines) == 3
        # Confidence normalized to 0.0 - 1.0
        assert page.confidence == pytest.approx(0.979, rel=1e-2)
        assert page.lines[0].confidence == pytest.approx(0.995, rel=1e-2)

    def test_textract_does_not_log_document_contents_or_credentials(self, caplog):
        mock_client = MagicMock()
        mock_client.detect_document_text.return_value = {
            "Blocks": [
                {"BlockType": "LINE", "Text": "TOP SECRET APPLICANT PII 987654", "Confidence": 99.0}
            ]
        }

        provider = TextractOCRProvider(client=mock_client)
        with caplog.at_level(logging.INFO):
            provider.extract_text_from_image(b"super_sensitive_bytes")

        # Verify logs do not contain raw document text or bytes
        log_output = caplog.text
        assert "TOP SECRET APPLICANT PII" not in log_output
        assert "super_sensitive_bytes" not in log_output


# ---------------------------------------------------------------------------
# 11. Deterministic Demo Baseline Maintained
# ---------------------------------------------------------------------------
class TestDeterministicDemoBaselineMaintained:
    """Verify that adding OCR capabilities did not alter baseline deterministic demo results."""

    def test_deterministic_demo_baseline_unaffected(self):
        from app.agent import assess_paperwork_deterministic

        assessment = assess_paperwork_deterministic("I want to complete the example application.")

        assert assessment.workflow_id == "example_application"
        assert assessment.ready is False
        assert assessment.completion_percentage == 20.0

        satisfied_names = [c.requirement_name for c in assessment.satisfied_requirements]
        assert "Address Proof" in satisfied_names

        missing_names = [c.requirement_name for c in assessment.missing_requirements]
        assert "Recent Photograph" in missing_names
        assert "Educational Certificate" in missing_names
        assert "Employment Reference" in missing_names

        conflict_names = [c.requirement_name for c in assessment.conflicts]
        assert "Identity Proof" in conflict_names or "Date of Birth Verification" in conflict_names
