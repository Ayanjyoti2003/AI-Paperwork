"""Paperwork Agent - Workflow requirements tools."""

from __future__ import annotations

import json
from pathlib import Path

from strands import tool

# Resolve the data/workflows directory relative to project root
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
WORKFLOWS_DIR = _PROJECT_ROOT / "data" / "workflows"


@tool
def get_workflow_requirements(workflow_id: str) -> str:
    """Load the requirements for a specific workflow from the workflow registry.

    Workflows are defined as JSON files in data/workflows/. Each workflow contains
    a list of requirements specifying what documents and evidence are needed.

    Args:
        workflow_id: The ID of the workflow to load (e.g., 'example_application').
    """
    if not WORKFLOWS_DIR.exists():
        return json.dumps({"error": "Workflows directory not found", "path": str(WORKFLOWS_DIR)})

    # Try to find the workflow file
    workflow_file = WORKFLOWS_DIR / f"{workflow_id}.json"
    if not workflow_file.exists():
        # List available workflows
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
