"""Paperwork Agent - Strands Agent setup and model provider configuration."""

from __future__ import annotations

import logging
import os
import sys

from strands import Agent

from app.prompts import SYSTEM_PROMPT
from app.tools.documents import (
    extract_document_facts,
    list_documents,
    read_document,
    search_documents,
)
from app.tools.requirements import get_workflow_requirements
from app.tools.verification import verify_requirements

logger = logging.getLogger(__name__)

# All tools available to the agent
ALL_TOOLS = [
    list_documents,
    search_documents,
    read_document,
    extract_document_facts,
    get_workflow_requirements,
    verify_requirements,
]


def _create_model():
    """Create the model provider based on environment variables.

    Supports:
        MODEL_PROVIDER=openai   -> OpenAIModel (requires OPENAI_API_KEY)
        MODEL_PROVIDER=anthropic -> AnthropicModel (requires ANTHROPIC_API_KEY)

    If MODEL_PROVIDER is not set, defaults to 'openai'.
    """
    provider = os.environ.get("MODEL_PROVIDER", "openai").lower()
    model_id = os.environ.get("MODEL_ID", "")

    if provider == "openai":
        api_key = os.environ.get("OPENAI_API_KEY", "")
        if not api_key or api_key.startswith("your-"):
            print("\n[ERROR] OPENAI_API_KEY is not set or is a placeholder.")
            print("   Set it in your .env file or as an environment variable.")
            print("   Example: OPENAI_API_KEY=sk-...")
            sys.exit(1)

        from strands.models.openai import OpenAIModel

        if not model_id:
            model_id = "gpt-4o"

        model = OpenAIModel(
            client_args={"api_key": api_key},
            model_id=model_id,
            params={"max_tokens": 4096, "temperature": 0.2},
        )
        logger.info(f"Using OpenAI provider with model: {model_id}")
        return model

    elif provider == "anthropic":
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key or api_key.startswith("your-"):
            print("\n[ERROR] ANTHROPIC_API_KEY is not set or is a placeholder.")
            print("   Set it in your .env file or as an environment variable.")
            print("   Example: ANTHROPIC_API_KEY=sk-ant-...")
            sys.exit(1)

        from strands.models.anthropic import AnthropicModel

        if not model_id:
            model_id = "claude-sonnet-4-6"

        model = AnthropicModel(
            client_args={"api_key": api_key},
            model_id=model_id,
            max_tokens=4096,
            params={"temperature": 0.2},
        )
        logger.info(f"Using Anthropic provider with model: {model_id}")
        return model

    else:
        print(f"\n[ERROR] Unsupported MODEL_PROVIDER: {provider}")
        print("   Supported values: openai, anthropic")
        sys.exit(1)


def create_agent() -> Agent:
    """Create and return the configured Paperwork Agent."""
    model = _create_model()

    agent = Agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        tools=ALL_TOOLS,
    )

    return agent
