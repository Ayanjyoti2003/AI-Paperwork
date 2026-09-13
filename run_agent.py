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

# Load .env file if it exists
from dotenv import load_dotenv
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


def print_banner():
    """Print a startup banner."""
    print("\n" + "=" * 60)
    print("  [PAPERWORK AGENT] - Phase 1")
    print("  Administrative Document Verification Assistant")
    print("=" * 60)

    provider = os.environ.get("MODEL_PROVIDER", "openai")
    model_id = os.environ.get("MODEL_ID", "(default)")
    print(f"\n  Provider:  {provider}")
    print(f"  Model:     {model_id}")

    docs_dir = Path(__file__).parent / "data" / "documents"
    if docs_dir.exists():
        doc_count = sum(1 for f in docs_dir.iterdir() if f.is_file())
        print(f"  Documents: {doc_count} files in data/documents/")
    else:
        print("  Documents: [!] data/documents/ not found")

    print("\n  Type your paperwork goal and press Enter.")
    print("  Type 'quit' or 'exit' to stop.")
    print("  Try: 'I want to complete the example application.'")
    print("-" * 60 + "\n")


def main():
    """Run the Paperwork Agent CLI."""
    setup_logging()
    print_banner()

    # Import here so env vars are loaded first
    from app.agent import create_agent
    from app.schemas import ReadinessAssessment

    try:
        agent = create_agent()
    except Exception as e:
        print(f"\n[ERROR] Failed to create agent: {e}")
        print("   Check your .env configuration and API keys.")
        sys.exit(1)

    print("[SUCCESS] Agent ready.\n")

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
            # Try with structured output for readiness assessments
            result = agent(user_input)

            # Print the agent's response text
            print("\n" + "-" * 40)
            print("Agent Response:")
            print("-" * 40)

            # The result object has the text output
            if hasattr(result, 'message') and result.message:
                # Extract text from the message
                if isinstance(result.message, dict) and 'content' in result.message:
                    for block in result.message['content']:
                        if isinstance(block, dict) and block.get('type') == 'text':
                            print(block['text'])
                elif isinstance(result.message, str):
                    print(result.message)
                else:
                    print(str(result))
            else:
                print(str(result))

        except Exception as e:
            print(f"\n❌ Error: {e}")
            logging.getLogger(__name__).exception("Agent error")

        print()


if __name__ == "__main__":
    main()
