"""Paperwork Agent - CLI entry point.

Usage:
    python run_agent.py

Requires:
    - MODEL_PROVIDER and corresponding API key in .env or environment
    - See .env.example for configuration
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

# Ensure backend root is on sys.path
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Load .env file if it exists (checks backend/ directory and current working directory)
from dotenv import load_dotenv
load_dotenv(backend_dir / ".env")
load_dotenv()


# Ensure stdout/stderr handle UTF-8 properly on Windows
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def setup_logging():
    """Configure logging based on LOG_LEVEL environment variable."""
    level = os.environ.get("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    # Reduce noise from HTTP libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("anthropic").setLevel(logging.WARNING)


def print_assessment(assessment, mode_label: str):
    """Print the structured assessment result with operating mode clearly indicated."""
    print("\n" + "=" * 60)
    print(f"  [STRUCTURED READINESS ASSESSMENT - {mode_label}]")
    print("=" * 60)
    print(f"  Execution Mode: {mode_label}")
    print(f"  Workflow:       {assessment.workflow_name} ({assessment.workflow_id})")
    print(f"  Status:         {'READY FOR SUBMISSION' if assessment.ready else 'NOT READY'}")
    print(f"  Completion:     {assessment.completion_percentage}%")

    if assessment.satisfied_requirements:
        print("\n  Satisfied Requirements:")
        for req in assessment.satisfied_requirements:
            print(f"    [OK] {req.requirement_name}")

    if assessment.missing_requirements:
        print("\n  Missing Requirements:")
        for req in assessment.missing_requirements:
            notes = f": {req.notes}" if req.notes else ""
            print(f"    [MISSING] {req.requirement_name}{notes}")

    if assessment.conflicts:
        print("\n  Detected Conflicts:")
        for req in assessment.conflicts:
            print(f"    [CONFLICT] {req.requirement_name}")
            for conf in req.conflicts:
                print(f"      Field '{conf.field}':")
                for val in conf.values:
                    print(f"        - {val.get('value')} (doc: {val.get('source_document')})")

    if assessment.recommended_next_actions:
        print("\n  Recommended Next Actions:")
        for i, action in enumerate(assessment.recommended_next_actions, 1):
            print(f"    {i}. {action}")
    print("=" * 60)


def print_banner(status, status_msg: str):
    """Print a startup banner indicating operating mode."""
    print("\n" + "=" * 60)
    print("  [PAPERWORK AGENT] - Intelligent Paperwork Assistant")
    print("=" * 60)

    provider = os.environ.get("MODEL_PROVIDER", "openai").lower()
    model_id = os.environ.get("MODEL_ID", "(default)")

    # Status-specific mode display
    if getattr(status, "value", str(status)) == "LIVE_READY":
        print("\n  OPERATING MODE: [LIVE STRANDS MODE]")
        print(f"  Provider:       {provider}")
        print(f"  Model:          {model_id}")
        print("  Status:         Real LLM agent will autonomously orchestrate tools.")
    else:
        status_val = getattr(status, "value", str(status))
        print("\n  OPERATING MODE: [DETERMINISTIC DEMO MODE]")
        print(f"  Live Status:    {status_val} - {status_msg}")
        print("  Notice:         Operating in offline deterministic mode without LLM calls.")
        print("                  To enable LIVE STRANDS MODE, set OPENAI_API_KEY or")
        print("                  ANTHROPIC_API_KEY in backend/.env")

    workflows_dir = Path(__file__).parent / "data" / "workflows"
    if workflows_dir.exists():
        wf_count = sum(1 for f in workflows_dir.glob("*.json") if f.is_file())
        print(f"\n  Workflows:      {wf_count} workflow(s) in data/workflows/")
    else:
        print("\n  Workflows:      [!] data/workflows/ not found")

    docs_dir = Path(__file__).parent / "data" / "documents"
    if docs_dir.exists():
        doc_count = sum(1 for f in docs_dir.iterdir() if f.is_file())
        print(f"  Documents:      {doc_count} files in data/documents/")
    else:
        print("  Documents:      [!] data/documents/ not found")

    print("\n  Type your paperwork goal and press Enter.")
    print("  Type 'quit' or 'exit' to stop.")
    print("  Try: 'I want to complete the example application.'")
    print("-" * 60 + "\n")


def main():
    """Run the Paperwork Agent CLI."""
    setup_logging()

    # Import here so env vars are loaded first
    from app.agent import (
        ModelStatus,
        assess_paperwork_deterministic,
        create_agent,
        get_model_status,
    )
    from app.schemas import ReadinessAssessment

    status, status_msg = get_model_status()
    print_banner(status, status_msg)

    agent = None
    if status == ModelStatus.LIVE_READY:
        try:
            agent = create_agent()
            print("[SUCCESS] Live Strands Agent initialized and ready.\n")
        except Exception as e:
            print(f"\n[ERROR] Failed to initialize live agent: {e}")
            print("        Cannot proceed in LIVE STRANDS MODE. Please check your credentials.")
            sys.exit(1)
    else:
        print(f"[INFO] Running in DETERMINISTIC DEMO MODE ({status.value}).\n")

    while True:
        try:
            user_input = input("You> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\nGoodbye!")
            break

        if not user_input:
            continue

        if user_input.lower() in {"quit", "exit", "q"}:
            print("\nGoodbye!")
            break

        print("\nThinking...\n")

        try:
            if status == ModelStatus.LIVE_READY:
                # Check if this is an assessment request or general prompt
                is_assessment_intent = any(
                    kw in user_input.lower()
                    for kw in [
                        "assess", "verify", "check", "ready", "complete",
                        "application", "paperwork", "prepare", "workflow", "example"
                    ]
                )

                if is_assessment_intent:
                    result = agent(user_input, structured_output_model=ReadinessAssessment)
                else:
                    result = agent(user_input)

                # Display structured assessment if returned
                if getattr(result, "structured_output", None) is not None:
                    print_assessment(result.structured_output, "LIVE STRANDS AGENT")

                # Print agent's message/thoughts if available
                if hasattr(result, "message") and result.message:
                    print("\n" + "-" * 40)
                    print("Agent Explanation:")
                    print("-" * 40)
                    if isinstance(result.message, dict) and "content" in result.message:
                        for block in result.message["content"]:
                            if isinstance(block, dict) and block.get("type") == "text":
                                print(block["text"])
                    elif isinstance(result.message, str):
                        print(result.message)
                    else:
                        print(str(result.message))
                elif getattr(result, "structured_output", None) is None:
                    print(str(result))

            else:
                # Offline deterministic pipeline
                assessment = assess_paperwork_deterministic(user_input)
                print_assessment(assessment, "DETERMINISTIC DEMO PIPELINE")

        except Exception as e:
            print(f"\n[ERROR] Execution failed: {e}")
            logging.getLogger(__name__).exception("Agent error")

        print()


if __name__ == "__main__":
    main()
