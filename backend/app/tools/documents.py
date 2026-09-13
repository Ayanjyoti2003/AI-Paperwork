"""Paperwork Agent - Document tools for listing, searching, reading, and extracting facts from documents."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from strands import tool

from app.ocr import (
    OCRProviderError,
    check_aws_credentials,
    extract_document_ocr,
)

# Resolve the data/documents directory relative to backend root
_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
DOCUMENTS_DIR = Path(os.environ.get("DOCUMENTS_DIR", _BACKEND_ROOT / "data" / "documents"))

# Supported file types and their readers
SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg"}
SUPPORTED_EXTENSIONS = {".txt", ".md", ".json", ".pdf"} | SUPPORTED_IMAGE_EXTENSIONS


@dataclass
class ExtractedDocument:
    """Normalized document text and provenance metadata."""

    content: str
    extraction_method: str = "native_text"
    confidence: Optional[float] = None
    page_count: int = 1


def _make_document_id(filename: str) -> str:
    """Create a stable document ID from a filename."""
    return hashlib.md5(filename.encode()).hexdigest()[:12]


def _read_text_file(path: Path) -> str:
    """Read a plain text file."""
    return path.read_text(encoding="utf-8", errors="replace")


def _read_pdf_file(path: Path) -> str:
    """Extract text from a PDF file using PyPDF2. Returns placeholder if extraction fails."""
    try:
        from PyPDF2 import PdfReader

        reader = PdfReader(str(path))
        pages = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text and text.strip():
                pages.append(f"[Page {i + 1}]\n{text.strip()}")
        if pages:
            return "\n\n".join(pages)
        return "[PDF text extraction unavailable — this PDF may contain scanned images requiring OCR]"
    except ImportError:
        return "[PDF support unavailable — install PyPDF2: pip install PyPDF2]"
    except Exception as e:
        return f"[PDF text extraction failed: {e}]"


def get_document_extraction(path: Path) -> ExtractedDocument:
    """Extract normalized text and provenance from a document.

    Automatically routes to:
    - native text reader for .txt, .md, .json
    - native PDF text extraction for text PDFs
    - OCR for image-only/scanned PDFs
    - OCR for images (.png, .jpg, .jpeg)
    """
    ext = path.suffix.lower()

    if ext in {".txt", ".md", ".json"}:
        return ExtractedDocument(
            content=_read_text_file(path),
            extraction_method="native_text",
            confidence=None,
            page_count=1,
        )

    if ext == ".pdf":
        # Check if native text extraction yields usable text
        try:
            from PyPDF2 import PdfReader

            reader = PdfReader(str(path))
            pages = []
            for i, page in enumerate(reader.pages):
                text = page.extract_text()
                if text and text.strip():
                    pages.append(f"[Page {i + 1}]\n{text.strip()}")

            if pages and sum(len(p) for p in pages) > 20:
                return ExtractedDocument(
                    content="\n\n".join(pages),
                    extraction_method="native_text",
                    confidence=None,
                    page_count=len(reader.pages),
                )
        except Exception:
            pass

        # If native PDF extraction returned no usable text, treat as scanned PDF requiring OCR
        try:
            ocr_res = extract_document_ocr(path)
            if not ocr_res.text:
                return ExtractedDocument(
                    content="[Scanned PDF processed by OCR — no readable text detected]",
                    extraction_method=ocr_res.extraction_method,
                    confidence=ocr_res.confidence,
                    page_count=len(ocr_res.pages) or 1,
                )
            return ExtractedDocument(
                content=ocr_res.text,
                extraction_method=ocr_res.extraction_method,
                confidence=ocr_res.confidence,
                page_count=len(ocr_res.pages) or 1,
            )
        except OCRProviderError as e:
            return ExtractedDocument(
                content=f"[OCR extraction failed: {e}]",
                extraction_method="error",
                confidence=None,
                page_count=1,
            )
        except Exception as e:
            return ExtractedDocument(
                content=f"[PDF extraction failed: {e}]",
                extraction_method="error",
                confidence=None,
                page_count=1,
            )

    if ext in SUPPORTED_IMAGE_EXTENSIONS:
        try:
            ocr_res = extract_document_ocr(path)
            if not ocr_res.text:
                return ExtractedDocument(
                    content="[Image processed by OCR — no readable text detected]",
                    extraction_method=ocr_res.extraction_method,
                    confidence=ocr_res.confidence,
                    page_count=1,
                )
            return ExtractedDocument(
                content=ocr_res.text,
                extraction_method=ocr_res.extraction_method,
                confidence=ocr_res.confidence,
                page_count=len(ocr_res.pages) or 1,
            )
        except OCRProviderError as e:
            return ExtractedDocument(
                content=f"[OCR extraction failed: {e}]",
                extraction_method="error",
                confidence=None,
                page_count=1,
            )
        except Exception as e:
            return ExtractedDocument(
                content=f"[Image OCR failed: {e}]",
                extraction_method="error",
                confidence=None,
                page_count=1,
            )

    return ExtractedDocument(
        content=f"[Unsupported file type: {ext}]",
        extraction_method="unsupported",
        confidence=None,
        page_count=1,
    )


def _read_file_content(path: Path) -> str:
    """Read file content based on extension, automatically invoking OCR when necessary."""
    return get_document_extraction(path).content


def _get_file_metadata(path: Path) -> dict:
    """Get basic file metadata."""
    stat = path.stat()
    return {
        "size_bytes": stat.st_size,
        "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
    }


# ---------- TOOLS ----------


@tool
def list_documents() -> str:
    """List all documents currently available in the user's local documents store.

    Use this tool early in a workflow to discover what files the user has provided
    before searching or reading.

    Returns:
        JSON string containing a list of documents with their stable document_id,
        filename, file_type, size_bytes, and modification timestamp.
    """
    import json

    if not DOCUMENTS_DIR.exists():
        return json.dumps({"error": "Documents directory not found", "path": str(DOCUMENTS_DIR)})

    documents = []
    for path in sorted(DOCUMENTS_DIR.iterdir()):
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
            meta = _get_file_metadata(path)
            ext = path.suffix.lower()
            if ext in {".txt", ".md", ".json"}:
                ext_method = "native_text"
            elif ext in SUPPORTED_IMAGE_EXTENSIONS:
                provider_env = os.environ.get("OCR_PROVIDER", "auto").lower()
                ext_method = "textract" if (provider_env == "textract" or (provider_env == "auto" and check_aws_credentials())) else "local_ocr"
            elif ext == ".pdf":
                ext_method = "native_text"
            else:
                ext_method = "native_text"

            documents.append({
                "document_id": _make_document_id(path.name),
                "filename": path.name,
                "file_type": path.suffix.lstrip(".").lower(),
                "size_bytes": meta["size_bytes"],
                "modified_at": meta["modified_at"],
                "extraction_method": ext_method,
            })

    return json.dumps({"documents": documents, "count": len(documents)}, indent=2)


@tool
def search_documents(query: str) -> str:
    """Search locally available documents for information relevant to a requirement.

    Use this to locate specific evidence needed for requirements (e.g., 'utility bill address',
    'degree graduation certificate', 'national identity card') without reading every file blindly.

    Args:
        query: Natural-language search query describing the needed evidence or document type.

    Returns:
        JSON string containing matching documents ranked by relevance score, with snippets
        highlighting where the terms were found.
    """
    import json

    if not DOCUMENTS_DIR.exists():
        return json.dumps({"error": "Documents directory not found"})

    # Normalize query into keywords
    query_lower = query.lower()
    keywords = [w for w in re.split(r"\W+", query_lower) if len(w) >= 2]

    if not keywords:
        return json.dumps({"results": [], "message": "No searchable keywords in query"})

    results = []
    for path in sorted(DOCUMENTS_DIR.iterdir()):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue

        content = _read_file_content(path)
        if content.startswith("["):  # Error/unsupported marker
            continue

        content_lower = content.lower()

        # Count keyword hits and find best snippet
        hit_count = 0
        best_snippet = ""
        best_snippet_score = 0

        for keyword in keywords:
            count = content_lower.count(keyword)
            hit_count += count

        if hit_count == 0:
            continue

        # Find the best snippet: the line with the most keyword hits
        lines = content.split("\n")
        for line in lines:
            line_lower = line.lower().strip()
            if not line_lower:
                continue
            line_score = sum(1 for kw in keywords if kw in line_lower)
            if line_score > best_snippet_score:
                best_snippet_score = line_score
                best_snippet = line.strip()[:300]

        # Simple relevance score: fraction of keywords found, weighted by hit density
        keywords_found = sum(1 for kw in keywords if kw in content_lower)
        relevance = round(keywords_found / len(keywords), 2)

        doc_id = _make_document_id(path.name)
        results.append({
            "document_id": doc_id,
            "filename": path.name,
            "snippet": best_snippet,
            "relevance_score": relevance,
        })

    # Sort by relevance descending
    results.sort(key=lambda r: r["relevance_score"], reverse=True)

    return json.dumps({"query": query, "results": results[:10]}, indent=2)


@tool
def read_document(document_id: str) -> str:
    """Read the full text content of a single document identified by its document_id.

    Use this only on promising documents identified via search_documents or list_documents
    when detailed context or full document inspection is required.

    Args:
        document_id: The stable document identifier (from list_documents or search_documents).

    Returns:
        JSON string containing document metadata and extracted text content.
    """
    import json

    if not DOCUMENTS_DIR.exists():
        return json.dumps({"error": "Documents directory not found"})

    # Find the file matching this document_id
    for path in DOCUMENTS_DIR.iterdir():
        if path.is_file() and _make_document_id(path.name) == document_id:
            meta = _get_file_metadata(path)
            extracted = get_document_extraction(path)
            content = extracted.content

            # Limit extremely large files to ~50KB of text
            if len(content) > 50_000:
                content = content[:50_000] + "\n\n[... content truncated at 50KB ...]"

            return json.dumps({
                "document_id": document_id,
                "filename": path.name,
                "file_type": path.suffix.lstrip(".").lower(),
                "size_bytes": meta["size_bytes"],
                "modified_at": meta["modified_at"],
                "extraction_method": extracted.extraction_method,
                "confidence": extracted.confidence,
                "content": content,
            }, indent=2)

    return json.dumps({"error": f"Document not found with id: {document_id}"})


@tool
def extract_document_facts(document_id: str, requested_fields: str) -> str:
    """Extract specific factual fields from a document with exact provenance.

    Use this after identifying a relevant document to pull structured fields
    (e.g., 'full_name,date_of_birth,address,nationality,id_number').
    Returns structured facts with source_document ID, confidence, and verbatim evidence snippets.

    Args:
        document_id: The stable document identifier to extract facts from.
        requested_fields: Comma-separated field names (e.g. 'full_name,date_of_birth') or list of field names.

    Returns:
        JSON string containing the list of extracted facts with provenance.
    """
    import json

    if not DOCUMENTS_DIR.exists():
        return json.dumps({"error": "Documents directory not found"})

    # Find the document
    target_path: Optional[Path] = None
    for path in DOCUMENTS_DIR.iterdir():
        if path.is_file() and _make_document_id(path.name) == document_id:
            target_path = path
            break

    if target_path is None:
        return json.dumps({"error": f"Document not found with id: {document_id}"})

    extracted = get_document_extraction(target_path)
    content = extracted.content
    if content.startswith("["):
        return json.dumps({
            "error": "Could not extract text from document",
            "detail": content,
        })

    if isinstance(requested_fields, list):
        fields = [str(f).strip() for f in requested_fields if str(f).strip()]
    elif isinstance(requested_fields, str):
        fields = [f.strip() for f in requested_fields.split(",") if f.strip()]
    else:
        fields = [str(requested_fields).strip()]
    facts = []

    for field in fields:
        # Try to find the field in the document using flexible pattern matching
        fact = _extract_single_fact(
            field=field,
            content=content,
            doc_id=_make_document_id(target_path.name),
            filename=target_path.name,
            extraction_method=extracted.extraction_method,
            ocr_confidence=extracted.confidence,
        )
        facts.append(fact)

    return json.dumps({
        "document_id": document_id,
        "filename": target_path.name,
        "extracted_facts": [f for f in facts],
    }, indent=2)


def _detect_page_number(match_start: int, content: str) -> Optional[int]:
    """Find which [Page X] section the match occurred in."""
    page_matches = list(re.finditer(r"\[Page\s+(\d+)\]", content[:match_start + 1]))
    if page_matches:
        try:
            return int(page_matches[-1].group(1))
        except (ValueError, IndexError):
            pass
    return 1


def _extract_single_fact(
    field: str,
    content: str,
    doc_id: str,
    filename: str,
    extraction_method: str = "native_text",
    ocr_confidence: Optional[float] = None,
) -> dict:
    """Try to extract a single fact from document content using keyword/pattern matching."""
    field_lower = field.lower().replace("_", " ")
    content_lower = content.lower()

    # Common field name variations
    field_variants = [field_lower]
    if " " in field_lower:
        field_variants.append(field_lower.replace(" ", "_"))
        field_variants.append(field_lower.replace(" ", ""))

    # Add common aliases
    aliases = {
        "full name": ["name", "full name", "applicant name", "holder name", "fullname"],
        "date of birth": ["date of birth", "dob", "birth date", "born", "dateofbirth"],
        "address": ["address", "residential address", "current address", "home address"],
        "phone": ["phone", "telephone", "mobile", "contact number"],
        "email": ["email", "e-mail", "email address"],
        "nationality": ["nationality", "citizenship"],
        "id number": ["id number", "identification number", "id no"],
        "photograph": ["photograph", "photo", "passport photo"],
    }

    for key, variants in aliases.items():
        if field_lower in variants or any(v in field_lower for v in variants):
            field_variants.extend(variants)

    field_variants = list(set(field_variants))

    # Search for the field in content
    for variant in field_variants:
        # Look for patterns like "Field: Value" or "Field - Value"
        patterns = [
            rf"(?i){re.escape(variant)}\s*[:=\-–]\s*(.+)",
            rf"(?i)\b{re.escape(variant)}\b[:\s]+(.+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                value = match.group(1).strip()
                # Clean up the value (take first line only)
                value = value.split("\n")[0].strip()
                # Get surrounding context for evidence
                start = max(0, match.start() - 20)
                end = min(len(content), match.end() + 50)
                snippet = content[start:end].strip()
                page_num = _detect_page_number(match.start(), content)
                conf = ocr_confidence if (extraction_method != "native_text" and ocr_confidence is not None) else "high"

                return {
                    "field": field,
                    "value": value,
                    "source_document": doc_id,
                    "source_page": page_num,
                    "page_number": page_num,
                    "confidence": conf,
                    "evidence_snippet": snippet,
                    "extraction_method": extraction_method,
                }

    # If not found via patterns, check if the field keyword exists at all
    found_anywhere = any(v in content_lower for v in field_variants)

    if found_anywhere:
        # Field keyword found but couldn't extract a clean value
        # Find the line containing the keyword for context
        for line in content.split("\n"):
            if any(v in line.lower() for v in field_variants):
                return {
                    "field": field,
                    "value": None,
                    "source_document": doc_id,
                    "source_page": None,
                    "page_number": None,
                    "confidence": "low",
                    "evidence_snippet": line.strip()[:300],
                    "extraction_method": extraction_method,
                }

    return {
        "field": field,
        "value": None,
        "source_document": doc_id,
        "source_page": None,
        "page_number": None,
        "confidence": "not_found",
        "evidence_snippet": None,
        "extraction_method": extraction_method,
    }
