from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from strands import tool

_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
WORKFLOWS_DIR = Path(os.environ.get("WORKFLOWS_DIR", _BACKEND_ROOT / "data" / "workflows"))


def _is_high_confidence(conf: Any) -> bool:
    """Check if confidence is high, supporting legacy strings and numeric scores."""
    if conf == "high":
        return True
    if isinstance(conf, (int, float)):
        return conf >= 0.7
    if isinstance(conf, str):
        try:
            return float(conf) >= 0.7
        except ValueError:
            pass
    return False


@tool
def verify_requirements(workflow_id: str, evidence_json: str) -> str:
    """Authoritative deterministic verification of collected evidence against workflow requirements.

    Performs deterministic rule checks to classify each requirement as satisfied, missing,
    conflict, or uncertain. Detects cross-document factual conflicts and calculates completion.

    Use this tool after extracting facts across documents to obtain the authoritative
    verification status before producing the final assessment.

    Args:
        workflow_id: The workflow ID to verify against (e.g., 'example_application').
        evidence_json: A JSON string, list of fact dicts, or dict with extracted facts. Each fact
            should include: field, value, source_document, confidence, evidence_snippet.

    Returns:
        JSON string containing the verification assessment with ready (bool), completion_percentage,
        categorized requirement checks (satisfied, missing, conflicts, uncertainties),
        and actionable recommended_next_actions.
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
    if isinstance(evidence_json, list):
        evidence = evidence_json
    elif isinstance(evidence_json, dict):
        evidence = evidence_json.get("evidence", [evidence_json])
    elif isinstance(evidence_json, str):
        try:
            parsed = json.loads(evidence_json)
            if isinstance(parsed, list):
                evidence = parsed
            elif isinstance(parsed, dict) and "evidence" in parsed:
                evidence = parsed["evidence"]
            elif isinstance(parsed, dict):
                evidence = [parsed]
            else:
                return json.dumps({"error": "evidence_json must be a JSON array of facts"})
        except json.JSONDecodeError as e:
            return json.dumps({"error": f"Invalid evidence JSON: {e}"})
    else:
        return json.dumps({"error": "evidence_json must be a JSON array of facts or a list"})

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

        accepted_types = req.get("accepted_evidence_types", [])
        types_hint = ", ".join(t.replace("_", " ") for t in accepted_types) if accepted_types else "supporting documentation"
        validation_hint = req.get("validation_hints", "")

        if not matching_evidence:
            # No evidence at all
            if required:
                note_text = (
                    f"{req_name} is required but no supporting document was found in the available documents. "
                    f"Please provide an acceptable document ({types_hint})."
                )
            else:
                note_text = (
                    f"{req_name} is optional and no supporting document was found in the available documents. "
                    f"Accepted formats: {types_hint}."
                )
            if validation_hint:
                note_text += f" Note: {validation_hint}"

            checks.append({
                "requirement_id": req_id,
                "requirement_name": req_name,
                "status": "missing",
                "evidence": [],
                "conflicts": [],
                "notes": note_text,
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
            _is_high_confidence(f.get("confidence")) and f.get("value") is not None
            for f in matching_evidence
        )
        has_value = any(f.get("value") is not None for f in matching_evidence)

        if conflicts:
            status = "conflict"
            notes = (
                f"Conflicting values found across documents for: {[c['field'] for c in conflicts]}. "
                f"Discrepancy must be clarified or corrected before submission."
            )
        elif has_high_confidence:
            status = "satisfied"
            satisfied_count += 1
            notes = None
        elif has_value:
            status = "uncertain"
            notes = f"Evidence found but confidence is not high ({types_hint})"
        else:
            status = "missing"
            notes = f"Field referenced but no reliable value extracted. Please provide {types_hint}."

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
        req_item = next((r for r in requirements if r["id"] == c["requirement_id"]), {})
        req_types = req_item.get("accepted_evidence_types", [])
        types_str = f" (accepted: {', '.join(t.replace('_', ' ') for t in req_types)})" if req_types else ""
        actions.append(f"Provide supporting document for {c['requirement_name']}{types_str}")
    for c in conflict_checks:
        fields = [conf["field"] for conf in c["conflicts"]]
        actions.append(f"Resolve conflicting values for {', '.join(fields)} in {c['requirement_name']}")
    for c in uncertain:
        actions.append(f"Verify and clarify evidence for: {c['requirement_name']}")

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
