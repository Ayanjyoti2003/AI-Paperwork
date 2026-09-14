"""Paperwork Agent - Workflow discovery and requirements loading tools."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from strands import tool

# Resolve the data/workflows directory relative to backend root
_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
WORKFLOWS_DIR = Path(os.environ.get("WORKFLOWS_DIR", _BACKEND_ROOT / "data" / "workflows"))


@tool
def discover_workflow(user_goal: str) -> str:
    """Discover which locally available paperwork workflow matches a user's goal.

    Inspects all workflow definitions in data/workflows/ to find the most relevant
    match based on workflow IDs, names, descriptions, and required paperwork types.

    Use this tool at the start of an interaction to identify the target workflow
    before loading requirements or inspecting documents.

    Args:
        user_goal: The user's natural language goal or request
            (e.g., 'I want to complete the example application', 'need help with passport renewal').

    Returns:
        A JSON string containing the discovered workflow ID, name, confidence score,
        and reason, or status='workflow_not_found' with a list of available workflows.
    """
    if not WORKFLOWS_DIR.exists():
        return json.dumps({
            "status": "workflow_not_found",
            "message": "Workflows directory not found",
            "available_workflows": [],
        })

    # Load all available workflows
    loaded_workflows = []
    for path in sorted(WORKFLOWS_DIR.glob("*.json")):
        if not path.is_file():
            continue
        try:
            wf = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(wf, dict) and "workflow_id" in wf:
                loaded_workflows.append(wf)
        except Exception:
            continue

    if not loaded_workflows:
        return json.dumps({
            "status": "workflow_not_found",
            "message": "No workflow definitions found in data/workflows/",
            "available_workflows": [],
        })

    # Clean and tokenize user goal
    goal_clean = (user_goal or "").strip().lower()
    goal_words = set(re.findall(r"\b[a-z0-9_]{2,}\b", goal_clean))

    if not goal_words:
        return json.dumps({
            "status": "workflow_not_found",
            "message": "User goal is empty or contains no searchable terms.",
            "available_workflows": [
                {"workflow_id": w["workflow_id"], "workflow_name": w.get("workflow_name", w["workflow_id"])}
                for w in loaded_workflows
            ],
        })

    best_wf = None
    best_score = 0.0
    best_reason = ""

    for wf in loaded_workflows:
        wf_id = wf.get("workflow_id", "").lower()
        wf_name = wf.get("workflow_name", "").lower()
        wf_desc = wf.get("description", "").lower()

        wf_id_words = set(re.findall(r"\b[a-z0-9]{2,}\b", wf_id.replace("_", " ")))
        wf_name_words = set(re.findall(r"\b[a-z0-9]{2,}\b", wf_name))
        wf_desc_words = set(re.findall(r"\b[a-z0-9]{2,}\b", wf_desc))

        score = 0.0
        reason_parts = []

        # 1. Exact or near-exact match on ID or Name
        if wf_id in goal_clean or wf_id.replace("_", " ") in goal_clean:
            score += 0.70
            reason_parts.append(f"direct mention of workflow ID '{wf_id}'")
        elif wf_id_words and wf_id_words.issubset(goal_words):
            score += 0.60
            reason_parts.append(f"matched all keywords from workflow ID '{wf_id}'")

        if wf_name and wf_name in goal_clean:
            score += 0.60
            reason_parts.append(f"direct mention of workflow name '{wf.get('workflow_name')}'")
        else:
            # Overlap with workflow name words
            name_overlap = goal_words.intersection(wf_name_words)
            if name_overlap:
                ratio = len(name_overlap) / len(wf_name_words)
                score += 0.40 * ratio
                reason_parts.append(f"matched name keywords: {sorted(name_overlap)}")

        # Overlap with description keywords
        desc_overlap = goal_words.intersection(wf_desc_words)
        if desc_overlap:
            score += min(0.20, len(desc_overlap) * 0.05)
            reason_parts.append(f"matched description keywords: {sorted(desc_overlap)}")

        score = min(1.0, score)

        if score > best_score:
            best_score = score
            best_wf = wf
            best_reason = "; ".join(reason_parts) if reason_parts else "Keyword similarity"

    # Require minimum confidence threshold to avoid guessing
    CONFIDENCE_THRESHOLD = 0.30

    if best_wf and best_score >= CONFIDENCE_THRESHOLD:
        return json.dumps({
            "status": "found",
            "workflow_id": best_wf["workflow_id"],
            "workflow_name": best_wf.get("workflow_name", best_wf["workflow_id"]),
            "confidence": round(best_score, 2),
            "reason": best_reason,
            "dynamically_generated": False,
        }, indent=2)

    # If dynamic workflow generation is explicitly enabled via environment variable
    if os.environ.get("AUTO_GENERATE_WORKFLOWS", "false").lower() in ("true", "1"):
        try:
            from app.workflow_generator import generate_and_register_workflow
            generated = generate_and_register_workflow(user_goal)
            return json.dumps({
                "status": "found",
                "workflow_id": generated["workflow_id"],
                "workflow_name": generated.get("workflow_name", generated["workflow_id"]),
                "confidence": 0.95,
                "reason": f"Dynamically generated checklist and verification rules for '{user_goal}'",
                "dynamically_generated": True,
            }, indent=2)
        except Exception:
            pass

    return json.dumps({
        "status": "workflow_not_found",
        "message": f"No suitable workflow could be confidently identified for goal: '{user_goal}'.",
        "available_workflows": [
            {
                "workflow_id": w["workflow_id"],
                "workflow_name": w.get("workflow_name", w["workflow_id"]),
                "description": w.get("description", ""),
            }
            for w in loaded_workflows
        ],
    }, indent=2)



@tool
def get_workflow_requirements(workflow_id: str) -> str:
    """Retrieve the formal requirements and accepted evidence types for a given paperwork workflow.

    Call this tool after identifying the target workflow with discover_workflow.
    Returns the full list of required and optional requirements, accepted evidence
    document types, relevant factual fields, and validation hints.

    Args:
        workflow_id: The identifier of the workflow (e.g., 'example_application').

    Returns:
        JSON string containing the workflow metadata and list of requirements with
        accepted evidence types, relevant fields, and validation hints.
    """
    if not WORKFLOWS_DIR.exists():
        return json.dumps({"error": "Workflows directory not found", "path": str(WORKFLOWS_DIR)})

    workflow_file = WORKFLOWS_DIR / f"{workflow_id}.json"
    if not workflow_file.exists():
        available = [
            f.stem for f in WORKFLOWS_DIR.glob("*.json") if f.is_file()
        ]
        return json.dumps({
            "error": f"Workflow not found: {workflow_id}",
            "available_workflows": available,
        })

    try:
        data = json.loads(workflow_file.read_text(encoding="utf-8"))
        return json.dumps(data, indent=2)
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Malformed workflow JSON: {e}"})
    except Exception as e:
        return json.dumps({"error": f"Failed to load workflow: {e}"})
