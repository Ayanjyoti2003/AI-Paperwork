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
from app.tools.requirements import discover_workflow, get_workflow_requirements
from app.tools.verification import verify_requirements

logger = logging.getLogger(__name__)

# All tools available to the agent (7 core tools)
ALL_TOOLS = [
    discover_workflow,
    get_workflow_requirements,
    list_documents,
    search_documents,
    read_document,
    extract_document_facts,
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
            raise ValueError(
                "OPENAI_API_KEY is not set or is a placeholder. "
                "Set it in your .env file or as an environment variable."
            )

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
            raise ValueError(
                "ANTHROPIC_API_KEY is not set or is a placeholder. "
                "Set it in your .env file or as an environment variable."
            )

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
        raise ValueError(
            f"Unsupported MODEL_PROVIDER: {provider}. Supported values: openai, anthropic"
        )


def create_agent(
    model=None,
    structured_output_model: type | None = None,
) -> Agent:
    """Create and return the configured Paperwork Agent.

    Args:
        model: Optional custom Model instance. If not provided, creates provider from env.
        structured_output_model: Optional Pydantic model for default structured output.
    """
    if model is None:
        model = _create_model()

    agent = Agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        tools=ALL_TOOLS,
        structured_output_model=structured_output_model,
    )

    return agent


def assess_paperwork(
    goal: str,
    agent: Agent | None = None,
):
    """Run the paperwork agent on a goal and return the validated ReadinessAssessment.

    Uses the current Strands SDK structured output mechanism (structured_output_model).

    Args:
        goal: The user's paperwork goal or instructions.
        agent: Optional existing Agent instance.

    Returns:
        ReadinessAssessment: Validated Pydantic structured output model.
    """
    from app.schemas import ReadinessAssessment

    if agent is None:
        agent = create_agent()

    result = agent(goal, structured_output_model=ReadinessAssessment)
    if getattr(result, "structured_output", None) is not None:
        return result.structured_output

    raise RuntimeError(
        "Agent execution completed but did not produce a validated ReadinessAssessment structured output."
    )
