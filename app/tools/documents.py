"""Paperwork Agent - Document tools for listing, searching, reading, and extracting facts from documents."""

from __future__ import annotations

import hashlib
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from strands import tool

# Resolve the data/documents directory relative to project root
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DOCUMENTS_DIR = _PROJECT_ROOT / "data" / "documents"

# Supported file types and their readers
SUPPORTED_EXTENSIONS = {".txt", ".md", ".json", ".pdf"}


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


def _read_file_content(path: Path) -> str:
    """Read file content based on extension."""
    ext = path.suffix.lower()
    if ext == ".pdf":
        return _read_pdf_file(path)
    elif ext in {".txt", ".md", ".json"}:
        return _read_text_file(path)
    else:
        return f"[Unsupported file type: {ext}]"


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
    """List all documents currently available in the data/documents directory.

    Returns a JSON-formatted list of documents with their IDs, filenames,
    file types, sizes, and modification timestamps.
    """
    import json

    if not DOCUMENTS_DIR.exists():
        return json.dumps({"error": "Documents directory not found", "path": str(DOCUMENTS_DIR)})

    documents = []
    for path in sorted(DOCUMENTS_DIR.iterdir()):
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
            meta = _get_file_metadata(path)
            documents.append({
                "document_id": _make_document_id(path.name),
                "filename": path.name,
                "file_type": path.suffix.lstrip(".").lower(),
                "size_bytes": meta["size_bytes"],
                "modified_at": meta["modified_at"],
            })

    return json.dumps({"documents": documents, "count": len(documents)}, indent=2)


@tool
def search_documents(query: str) -> str:
    """Search locally available documents for information relevant to a natural-language query.

    Uses normalized keyword matching with simple relevance scoring. Returns matching
    documents with relevant snippets and scores.

    Args:
        query: A natural-language search query (e.g., 'date of birth', 'address proof').
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
    """Read the full contents of a document identified by its document_id.

    Returns the document metadata and extracted text content.

    Args:
        document_id: The stable document identifier (from list_documents or search_documents).
    """
    import json

    if not DOCUMENTS_DIR.exists():
        return json.dumps({"error": "Documents directory not found"})

    # Find the file matching this document_id
    for path in DOCUMENTS_DIR.iterdir():
        if path.is_file() and _make_document_id(path.name) == document_id:
            meta = _get_file_metadata(path)
            content = _read_file_content(path)

            # Limit extremely large files to ~50KB of text
            if len(content) > 50_000:
                content = content[:50_000] + "\n\n[... content truncated at 50KB ...]"

            return json.dumps({
                "document_id": document_id,
                "filename": path.name,
                "file_type": path.suffix.lstrip(".").lower(),
                "size_bytes": meta["size_bytes"],
                "modified_at": meta["modified_at"],
                "content": content,
            }, indent=2)

    return json.dumps({"error": f"Document not found with id: {document_id}"})


@tool
def extract_document_facts(document_id: str, requested_fields: str) -> str:
    """Extract specific factual fields from a document.

    Searches the document text for evidence of the requested fields using
    pattern matching and keyword detection. Returns structured facts with
    provenance (source document, evidence snippet, confidence).

    The LLM agent should interpret and refine these extractions as needed.

    Args:
        document_id: The document to extract facts from.
        requested_fields: Comma-separated list of fields to look for (e.g., 'full_name,date_of_birth,address').
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

    content = _read_file_content(target_path)
    if content.startswith("["):
        return json.dumps({
            "error": "Could not extract text from document",
            "detail": content,
        })

    fields = [f.strip() for f in requested_fields.split(",") if f.strip()]
    facts = []

    for field in fields:
        # Try to find the field in the document using flexible pattern matching
        fact = _extract_single_fact(field, content, _make_document_id(target_path.name), target_path.name)
        facts.append(fact)

    return json.dumps({
        "document_id": document_id,
        "filename": target_path.name,
        "extracted_facts": [f for f in facts],
    }, indent=2)


def _extract_single_fact(field: str, content: str, doc_id: str, filename: str) -> dict:
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
        "full name": ["name", "full name", "applicant name", "holder name"],
        "date of birth": ["date of birth", "dob", "birth date", "born"],
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

                return {
                    "field": field,
                    "value": value,
                    "source_document": doc_id,
                    "source_page": None,
                    "confidence": "high",
                    "evidence_snippet": snippet,
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
                    "confidence": "low",
                    "evidence_snippet": line.strip()[:300],
                }

    return {
        "field": field,
        "value": None,
        "source_document": doc_id,
        "source_page": None,
        "confidence": "not_found",
        "evidence_snippet": None,
    }
