"""Paperwork Agent - Verification tool for checking requirements against evidence."""

from __future__ import annotations

import json
from pathlib import Path

from strands import tool

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
WORKFLOWS_DIR = _PROJECT_ROOT / "data" / "workflows"


@tool
def verify_requirements(workflow_id: str, evidence_json: str) -> str:
    """Verify whether collected evidence satisfies the requirements of a workflow.

    Performs deterministic checks to classify each requirement as satisfied, missing,
    conflict, or uncertain. Detects factual conflicts across documents.

    Args:
        workflow_id: The workflow to verify against (e.g., 'example_application').
        evidence_json: A JSON string containing a list of extracted facts. Each fact
            should have: field, value, source_document, confidence, evidence_snippet.
            Example: [{"field": "full_name", "value": "Jane Doe", "source_document": "abc123",
                       "confidence": "high", "evidence_snippet": "Name: Jane Doe"}]
    """
    # Load workflow
    workflow_file = WORKFLOWS_DIR / f"{workflow_id}.json"
    if not workflow_file.exists():
        return json.dumps({"error": f"Workflow not found: {workflow_id}"})

    try:
        workflow = json.loads(workflow_file.read_text(encoding="utf-8"))
    except Exception as e:
        return json.dumps({"error": f"Failed to load workflow: {e}"})

    # Parse evidence
    try:
        evidence = json.loads(evidence_json)
        if not isinstance(evidence, list):
            return json.dumps({"error": "evidence_json must be a JSON array of facts"})
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid evidence JSON: {e}"})

    requirements = workflow.get("requirements", [])
    checks = []
    satisfied_count = 0
    total_required = 0

    for req in requirements:
        req_id = req["id"]
        req_name = req["name"]
        required = req.get("required", True)
        relevant_fields = req.get("relevant_fields", [])

        if required:
            total_required += 1

        # Find evidence matching this requirement's fields
        matching_evidence = []
        for fact in evidence:
            fact_field = fact.get("field", "").lower().replace("_", " ")
            for rf in relevant_fields:
                rf_lower = rf.lower().replace("_", " ")
                if rf_lower in fact_field or fact_field in rf_lower:
                    matching_evidence.append(fact)
                    break

        if not matching_evidence:
            # No evidence at all
            checks.append({
                "requirement_id": req_id,
                "requirement_name": req_name,
                "status": "missing",
                "evidence": [],
                "conflicts": [],
                "notes": f"No evidence found for required fields: {relevant_fields}",
            })
            continue

        # Check for conflicts: same field, different values from different sources
        field_values: dict[str, list[dict]] = {}
        for fact in matching_evidence:
            field = fact.get("field", "")
            value = fact.get("value")
            source = fact.get("source_document", "unknown")
            if value is not None:
                field_values.setdefault(field, []).append({
                    "source_document": source,
                    "value": str(value).strip(),
                })

        conflicts = []
        for field, entries in field_values.items():
            unique_values = set(e["value"].lower() for e in entries)
            if len(unique_values) > 1:
                conflicts.append({
                    "field": field,
                    "values": entries,
                })

        # Check confidence levels
        has_high_confidence = any(
            f.get("confidence") == "high" and f.get("value") is not None
            for f in matching_evidence
        )
        has_value = any(f.get("value") is not None for f in matching_evidence)

        if conflicts:
            status = "conflict"
            notes = f"Conflicting values found for: {[c['field'] for c in conflicts]}"
        elif has_high_confidence:
            status = "satisfied"
            satisfied_count += 1
            notes = None
        elif has_value:
            status = "uncertain"
            notes = "Evidence found but confidence is not high"
        else:
            status = "missing"
            notes = "Fields referenced but no values extracted"

        checks.append({
            "requirement_id": req_id,
            "requirement_name": req_name,
            "status": status,
            "evidence": matching_evidence,
            "conflicts": conflicts,
            "notes": notes,
        })

    # Build the assessment
    completion = round((satisfied_count / total_required * 100) if total_required > 0 else 0, 1)
    ready = satisfied_count == total_required and not any(c["status"] == "conflict" for c in checks)

    # Categorize checks
    satisfied = [c for c in checks if c["status"] == "satisfied"]
    missing = [c for c in checks if c["status"] == "missing"]
    conflict_checks = [c for c in checks if c["status"] == "conflict"]
    uncertain = [c for c in checks if c["status"] == "uncertain"]

    # Generate recommended actions
    actions = []
    for c in missing:
        actions.append(f"Provide document(s) for: {c['requirement_name']}")
    for c in conflict_checks:
        fields = [conf["field"] for conf in c["conflicts"]]
        actions.append(f"Resolve conflicting values in: {c['requirement_name']} (fields: {fields})")
    for c in uncertain:
        actions.append(f"Verify/clarify evidence for: {c['requirement_name']}")

    assessment = {
        "workflow_id": workflow_id,
        "workflow_name": workflow.get("workflow_name", workflow_id),
        "ready": ready,
        "completion_percentage": completion,
        "satisfied_requirements": satisfied,
        "missing_requirements": missing,
        "conflicts": conflict_checks,
        "uncertainties": uncertain,
        "recommended_next_actions": actions,
    }

    return json.dumps(assessment, indent=2)
