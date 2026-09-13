"""Paperwork Agent - Phase 2 End-to-End Deterministic Demo.

Demonstrates the complete paperwork preparation workflow:
1. Workflow discovery from natural language goal
2. Requirement loading with validation hints
3. Document discovery and targeted search
4. Fact extraction with strict provenance
5. Deterministic verification with actionable missing notes & conflict detection
6. Production of validated Pydantic ReadinessAssessment

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

# Ensure backend root is on sys.path
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.schemas import ReadinessAssessment
from app.tools.documents import (
    extract_document_facts,
    list_documents,
    read_document,
    search_documents,
)
from app.tools.requirements import discover_workflow, get_workflow_requirements
from app.tools.verification import verify_requirements


def separator(title: str):
    print("\n" + "=" * 68)
    print(f"  {title}")
    print("=" * 68)


def main():
    user_goal = "I want to complete the example application."
    separator("PAPERWORK AGENT - PHASE 2 WORKFLOW DEMO")
    print(f"User Goal: \"{user_goal}\"\n")

    # Step 1: Workflow Discovery
    separator("STEP 1: Workflow Discovery (discover_workflow)")
    print(f"Discovering workflow for goal: '{user_goal}'...")
    discovery_raw = discover_workflow._tool_func(user_goal=user_goal)
    discovery = json.loads(discovery_raw)
    print(f"Discovery Status: {discovery.get('status')}")
    print(f"Matched Workflow: {discovery.get('workflow_name')} (ID: {discovery.get('workflow_id')})")
    print(f"Confidence:       {discovery.get('confidence')}")
    print(f"Reason:           {discovery.get('reason')}")

    target_workflow_id = discovery.get("workflow_id", "example_application")

    # Step 2: Load Workflow Requirements
    separator("STEP 2: Load Workflow Requirements (get_workflow_requirements)")
    wf_raw = get_workflow_requirements._tool_func(workflow_id=target_workflow_id)
    wf_data = json.loads(wf_raw)
    print(f"Workflow:    {wf_data['workflow_name']}")
    print(f"Description: {wf_data['description']}")
    print(f"Requirements ({len(wf_data['requirements'])}):")
    for r in wf_data["requirements"]:
        req_str = "REQUIRED" if r.get("required", True) else "OPTIONAL"
        hint = f" | Hint: {r['validation_hints']}" if r.get("validation_hints") else ""
        print(f"  - [{r['id']}] {r['name']} ({req_str}){hint}")
        print(f"    Accepted evidence: {r.get('accepted_evidence_types', [])}")
        print(f"    Relevant fields:   {r.get('relevant_fields', [])}")

    # Step 3: Discover Local User Documents
    separator("STEP 3: Document Discovery (list_documents)")
    docs_raw = list_documents._tool_func()
    docs_data = json.loads(docs_raw)
    print(f"Found {docs_data['count']} user documents in store:")
    doc_map = {}
    for doc in docs_data["documents"]:
        doc_map[doc["filename"]] = doc["document_id"]
        print(f"  - [{doc['document_id']}] {doc['filename']} ({doc['size_bytes']} bytes, .{doc['file_type']})")

    # Step 4: Targeted Document Search (based on requirements)
    separator("STEP 4: Targeted Search (search_documents)")
    queries = [
        "national identity card",
        "utility bill address proof",
        "degree certificate graduation",
    ]
    for q in queries:
        search_raw = search_documents._tool_func(query=q)
        search_data = json.loads(search_raw)
        top_hit = search_data.get("results", [])[0] if search_data.get("results") else None
        if top_hit:
            print(f"  Query '{q}':")
            print(f"    -> Best hit: {top_hit['filename']} (Relevance: {top_hit['relevance_score']})")
            print(f"       Snippet: \"{top_hit['snippet']}\"")

    # Step 5: Fact Extraction with Strict Provenance
    separator("STEP 5: Fact Extraction with Provenance (extract_document_facts)")
    all_facts = []

    extractions = [
        ("identity.txt", "full_name,date_of_birth,nationality,id_number,address"),
        ("address_proof.txt", "name,address"),
        ("certificate.txt", "full_name,date_of_birth,qualification,institution"),
    ]

    for fname, fields in extractions:
        doc_id = doc_map.get(fname)
        if not doc_id:
            continue
        facts_raw = extract_document_facts._tool_func(document_id=doc_id, requested_fields=fields)
        facts_data = json.loads(facts_raw)
        print(f"\nExtracted from {fname} (ID: {doc_id}):")
        for f in facts_data.get("extracted_facts", []):
            if f["value"]:
                all_facts.append(f)
                print(f"  - {f['field']}: '{f['value']}' (confidence: {f['confidence']})")
                print(f"    Evidence: \"{f['evidence_snippet']}\"")

    # Step 6: Deterministic Verification
    separator("STEP 6: Authoritative Verification (verify_requirements)")
    assessment_raw = verify_requirements._tool_func(
        workflow_id=target_workflow_id,
        evidence_json=json.dumps(all_facts),
    )
    # Validate against Pydantic schema
    assessment = ReadinessAssessment.model_validate_json(assessment_raw)

    print(f"Workflow:         {assessment.workflow_name} ({assessment.workflow_id})")
    print(f"Status:           {'READY FOR SUBMISSION' if assessment.ready else 'NOT READY'}")
    print(f"Completion:       {assessment.completion_percentage}%")
    print(f"Timestamp:        {assessment.assessed_at}")

    print("\nSatisfied Requirements:")
    for s in assessment.satisfied_requirements:
        print(f"  [OK] {s.requirement_name}")

    print("\nMissing Requirements (Actionable):")
    for m in assessment.missing_requirements:
        print(f"  [MISSING] {m.requirement_name}")
        print(f"            {m.notes}")

    print("\nConflicts Detected (First-Class Cross-Document Checks):")
    for c in assessment.conflicts:
        print(f"  [CONFLICT] {c.requirement_name}")
        for conf in c.conflicts:
            print(f"    Field '{conf.field}' values mismatch:")
            for val in conf.values:
                print(f"      - {val.get('value')} (Source doc: {val.get('source_document')})")

    print("\nRecommended Next Actions:")
    for i, action in enumerate(assessment.recommended_next_actions, 1):
        print(f"  {i}. {action}")

    separator("PHASE 2 DEMO COMPLETE - VALIDATED READINESS ASSESSMENT PRODUCED")


if __name__ == "__main__":
    main()
