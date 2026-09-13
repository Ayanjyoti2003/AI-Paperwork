"""Paperwork Agent - End-to-End Deterministic Demo.

Runs the complete document discovery, fact extraction, requirement loading,
and verification pipeline without requiring an external LLM API key.

Usage:
    python demo.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Ensure stdout handles UTF-8 on Windows
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from app.tools.documents import (
    extract_document_facts,
    list_documents,
    read_document,
    search_documents,
)
from app.tools.requirements import get_workflow_requirements
from app.tools.verification import verify_requirements


def separator(title: str):
    print("\n" + "=" * 65)
    print(f"  {title}")
    print("=" * 65)


def main():
    separator("PAPERWORK AGENT - END-TO-END DEMO (PHASE 1)")
    print("Goal: Evaluate user documents for 'example_application' workflow\n")

    # Step 1: Discover documents
    separator("STEP 1: Document Discovery (list_documents)")
    docs_raw = list_documents._tool_func()
    docs_data = json.loads(docs_raw)
    print(f"Found {docs_data['count']} documents:")
    doc_map = {}
    for doc in docs_data["documents"]:
        doc_map[doc["filename"]] = doc["document_id"]
        print(f"  - [{doc['document_id']}] {doc['filename']} ({doc['size_bytes']} bytes, .{doc['file_type']})")

    # Step 2: Search documents
    separator("STEP 2: Document Search (search_documents)")
    query = "identity card date of birth"
    print(f"Searching for: '{query}'")
    search_raw = search_documents._tool_func(query=query)
    search_data = json.loads(search_raw)
    for res in search_data.get("results", []):
        print(f"  - Hit: {res['filename']} (Relevance: {res['relevance_score']})")
        print(f"    Snippet: \"{res['snippet']}\"")

    # Step 3: Extract facts across all documents
    separator("STEP 3: Fact Extraction with Provenance (extract_document_facts)")
    all_facts = []

    extractions = [
        ("identity.txt", "full_name,date_of_birth,nationality,id_number,address"),
        ("address_proof.txt", "name,address"),
        ("certificate.txt", "full_name,date_of_birth,degree,institution"),
    ]

    for fname, fields in extractions:
        doc_id = doc_map.get(fname)
        if not doc_id:
            continue
        facts_raw = extract_document_facts._tool_func(document_id=doc_id, requested_fields=fields)
        facts_data = json.loads(facts_raw)
        print(f"\nExtracted from {fname}:")
        for f in facts_data.get("extracted_facts", []):
            if f["value"]:
                all_facts.append(f)
                print(f"  - {f['field']}: '{f['value']}' (confidence: {f['confidence']}, doc: {f['source_document']})")

    # Step 4: Load workflow requirements
    separator("STEP 4: Load Workflow Requirements (get_workflow_requirements)")
    wf_raw = get_workflow_requirements._tool_func(workflow_id="example_application")
    wf_data = json.loads(wf_raw)
    print(f"Workflow: {wf_data['workflow_name']}")
    print(f"Description: {wf_data['description']}")
    print(f"Requirements ({len(wf_data['requirements'])}):")
    for r in wf_data["requirements"]:
        req_str = "REQUIRED" if r.get("required", True) else "OPTIONAL"
        print(f"  - [{r['id']}] {r['name']} ({req_str})")
        print(f"    Relevant fields: {r.get('relevant_fields', [])}")

    # Step 5: Verify requirements against evidence
    separator("STEP 5: Deterministic Verification (verify_requirements)")
    assessment_raw = verify_requirements._tool_func(
        workflow_id="example_application",
        evidence_json=json.dumps(all_facts),
    )
    assessment = json.loads(assessment_raw)

    print(f"Workflow:              {assessment['workflow_name']}")
    print(f"Readiness Status:      {'READY FOR SUBMISSION' if assessment['ready'] else 'NOT READY'}")
    print(f"Completion:            {assessment['completion_percentage']}%")

    print("\nSatisfied Requirements:")
    for s in assessment.get("satisfied_requirements", []):
        print(f"  [OK] {s['requirement_name']}")

    print("\nMissing Requirements:")
    for m in assessment.get("missing_requirements", []):
        print(f"  [MISSING] {m['requirement_name']}: {m['notes']}")

    print("\nConflicts Detected:")
    for c in assessment.get("conflicts", []):
        print(f"  [CONFLICT] {c['requirement_name']}: {c['notes']}")
        for conf in c.get("conflicts", []):
            print(f"    Field '{conf['field']}':")
            for val in conf.get("values", []):
                print(f"      - {val['value']} (from {val['source_document']})")

    print("\nRecommended Actions:")
    for i, action in enumerate(assessment.get("recommended_next_actions", []), 1):
        print(f"  {i}. {action}")

    separator("DEMO COMPLETE")


if __name__ == "__main__":
    main()
