"""Paperwork Agent - Strands Agent setup and model provider configuration."""

from __future__ import annotations

import logging
import os
import sys
import uuid
from enum import Enum

from strands import Agent
from strands.hooks import (
    AfterInvocationEvent,
    AfterToolCallEvent,
    BeforeInvocationEvent,
    BeforeToolCallEvent,
    HookProvider,
    HookRegistry,
)

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
obs_logger = logging.getLogger("app.observability")


class ModelStatus(str, Enum):
    """Status of model provider credentials configuration."""

    LIVE_READY = "LIVE_READY"
    NO_CREDENTIALS = "NO_CREDENTIALS"
    INVALID_PROVIDER = "INVALID_PROVIDER"


def get_model_status() -> tuple[ModelStatus, str]:
    """Inspect environment variables to determine whether live credentials are configured.

    Performs zero network requests. The actual operational validity of credentials
    against upstream provider APIs is only determined upon real model invocation.

    Returns:
        tuple[ModelStatus, str]: (status, descriptive_message)
    """
    provider = os.environ.get("MODEL_PROVIDER", "openai").strip().lower()
    supported = {"openai", "anthropic", "groq", "ollama", "openrouter", "local"}
    if provider not in supported:
        return (
            ModelStatus.INVALID_PROVIDER,
            f"Unsupported MODEL_PROVIDER: '{provider}'. Supported: {', '.join(sorted(supported))}",
        )

    if provider in {"ollama", "local"}:
        model_id = os.environ.get("MODEL_ID", "llama3.2" if provider == "ollama" else "local-model")
        return (
            ModelStatus.LIVE_READY,
            f"{provider.capitalize()} local provider configured (model: {model_id})",
        )

    elif provider == "groq":
        key = os.environ.get("GROQ_API_KEY", "").strip()
        if not key or key.startswith("your-"):
            return (
                ModelStatus.NO_CREDENTIALS,
                "GROQ_API_KEY is not set or is an obvious placeholder.",
            )
        model_id = os.environ.get("MODEL_ID", "llama-3.3-70b-versatile")
        return (
            ModelStatus.LIVE_READY,
            f"Groq credential configured (model: {model_id})",
        )

    elif provider == "openrouter":
        key = os.environ.get("OPENROUTER_API_KEY", "").strip()
        if not key or key.startswith("your-"):
            return (
                ModelStatus.NO_CREDENTIALS,
                "OPENROUTER_API_KEY is not set or is an obvious placeholder.",
            )
        model_id = os.environ.get("MODEL_ID", "meta-llama/llama-3.2-3b-instruct:free")
        return (
            ModelStatus.LIVE_READY,
            f"OpenRouter credential configured (model: {model_id})",
        )

    elif provider == "openai":
        key = os.environ.get("OPENAI_API_KEY", "").strip()
        if not key or key.startswith("your-") or key == "your-openai-api-key-here":
            return (
                ModelStatus.NO_CREDENTIALS,
                "OPENAI_API_KEY is not set or is an obvious placeholder.",
            )
        model_id = os.environ.get("MODEL_ID", "gpt-4o")
        return (
            ModelStatus.LIVE_READY,
            f"OpenAI credential configured (model: {model_id})",
        )

    elif provider == "anthropic":
        key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
        if not key or key.startswith("your-") or key == "your-anthropic-api-key-here":
            return (
                ModelStatus.NO_CREDENTIALS,
                "ANTHROPIC_API_KEY is not set or is an obvious placeholder.",
            )
        model_id = os.environ.get("MODEL_ID", "claude-sonnet-4-6")
        return (
            ModelStatus.LIVE_READY,
            f"Anthropic credential configured (model: {model_id})",
        )

    return (ModelStatus.INVALID_PROVIDER, f"Unsupported MODEL_PROVIDER: '{provider}'")


class SafeAgentObservabilityHook(HookProvider):
    """Safe, non-sensitive observability hook for live Strands Agent execution.

    Subscribes to Strands SDK hook events to log execution flow without exposing
    user prompts, tool arguments, tool results, document contents, extracted facts,
    PII, API keys, or authorization headers.
    """

    def __init__(self, logger_instance: logging.Logger | None = None) -> None:
        self._logger = logger_instance or obs_logger
        self._current_invocation_id: str = ""

    def register_hooks(self, registry: HookRegistry) -> None:
        registry.add_callback(BeforeInvocationEvent, self.on_invocation_start)
        registry.add_callback(AfterInvocationEvent, self.on_invocation_complete)
        registry.add_callback(BeforeToolCallEvent, self.on_tool_call)
        registry.add_callback(AfterToolCallEvent, self.on_tool_result)

    def on_invocation_start(self, event: BeforeInvocationEvent) -> None:
        self._current_invocation_id = f"inv_{uuid.uuid4().hex[:8]}"
        self._logger.info(f"LIVE_AGENT_START invocation_id={self._current_invocation_id}")

    def on_invocation_complete(self, event: AfterInvocationEvent) -> None:
        inv_id = self._current_invocation_id or "inv_unknown"
        status = "failure" if getattr(event, "exception", None) else "success"
        self._logger.info(f"LIVE_AGENT_COMPLETE {status} invocation_id={inv_id}")

    def on_tool_call(self, event: BeforeToolCallEvent) -> None:
        tool_name = "unknown_tool"
        if hasattr(event, "tool_use") and isinstance(event.tool_use, dict):
            tool_name = event.tool_use.get("name", "unknown_tool")
        elif hasattr(event, "selected_tool") and event.selected_tool:
            tool_name = getattr(event.selected_tool, "name", str(event.selected_tool))
        self._logger.info(f"TOOL_CALL {tool_name}")

    def on_tool_result(self, event: AfterToolCallEvent) -> None:
        tool_name = "unknown_tool"
        if hasattr(event, "tool_use") and isinstance(event.tool_use, dict):
            tool_name = event.tool_use.get("name", "unknown_tool")
        elif hasattr(event, "selected_tool") and event.selected_tool:
            tool_name = getattr(event.selected_tool, "name", str(event.selected_tool))

        status = "failure" if getattr(event, "exception", None) else "success"
        duration = getattr(event, "duration", None)
        if duration is not None and isinstance(duration, (int, float)):
            self._logger.info(f"TOOL_RESULT {tool_name} {status} duration={duration:.3f}s")
        else:
            self._logger.info(f"TOOL_RESULT {tool_name} {status}")

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
        MODEL_PROVIDER=groq        -> OpenAIModel with Groq endpoint (FREE tier open source models: Llama 3.3, DeepSeek R1)
        MODEL_PROVIDER=ollama      -> OpenAIModel with local Ollama endpoint (100% Free local models)
        MODEL_PROVIDER=openrouter  -> OpenAIModel with OpenRouter endpoint (FREE tier models available)
        MODEL_PROVIDER=local       -> OpenAIModel with custom local base_url (LM Studio, vLLM)
        MODEL_PROVIDER=openai      -> OpenAIModel (requires OPENAI_API_KEY)
        MODEL_PROVIDER=anthropic   -> AnthropicModel (requires ANTHROPIC_API_KEY)
    """
    from strands.models.openai import OpenAIModel

    provider = os.environ.get("MODEL_PROVIDER", "openai").lower()
    model_id = os.environ.get("MODEL_ID", "")

    if provider == "groq":
        api_key = os.environ.get("GROQ_API_KEY", "")
        if not api_key or api_key.startswith("your-"):
            raise ValueError(
                "GROQ_API_KEY is not set. Get a free key at https://console.groq.com/keys "
                "and add it to your .env file."
            )
        if not model_id:
            model_id = "llama-3.3-70b-versatile"

        model = OpenAIModel(
            client_args={
                "api_key": api_key,
                "base_url": "https://api.groq.com/openai/v1",
            },
            model_id=model_id,
            params={"max_tokens": 4096, "temperature": 0.2},
        )
        logger.info(f"Using Groq (Open Source) provider with model: {model_id}")
        return model

    elif provider == "ollama":
        base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")
        if not model_id:
            model_id = "llama3.2"

        model = OpenAIModel(
            client_args={
                "api_key": "ollama",
                "base_url": base_url,
            },
            model_id=model_id,
            params={"max_tokens": 4096, "temperature": 0.2},
        )
        logger.info(f"Using Ollama local provider ({base_url}) with model: {model_id}")
        return model

    elif provider == "openrouter":
        api_key = os.environ.get("OPENROUTER_API_KEY", "")
        if not api_key or api_key.startswith("your-"):
            raise ValueError("OPENROUTER_API_KEY is not set. Get a free key at https://openrouter.ai")
        if not model_id:
            model_id = "meta-llama/llama-3.2-3b-instruct:free"

        model = OpenAIModel(
            client_args={
                "api_key": api_key,
                "base_url": "https://openrouter.ai/api/v1",
            },
            model_id=model_id,
            params={"max_tokens": 4096, "temperature": 0.2},
        )
        logger.info(f"Using OpenRouter provider with model: {model_id}")
        return model

    elif provider == "local":
        base_url = os.environ.get("OPENAI_BASE_URL", os.environ.get("LOCAL_BASE_URL", "http://localhost:1234/v1"))
        if not model_id:
            model_id = "local-model"

        model = OpenAIModel(
            client_args={
                "api_key": "not-needed",
                "base_url": base_url,
            },
            model_id=model_id,
            params={"max_tokens": 4096, "temperature": 0.2},
        )
        logger.info(f"Using Local provider ({base_url}) with model: {model_id}")
        return model

    elif provider == "openai":
        api_key = os.environ.get("OPENAI_API_KEY", "")
        if not api_key or api_key.startswith("your-"):
            raise ValueError(
                "OPENAI_API_KEY is not set or is a placeholder. "
                "Set it in your .env file or as an environment variable."
            )
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
            f"Unsupported MODEL_PROVIDER: {provider}. Supported values: groq, ollama, openrouter, local, openai, anthropic"
        )



def create_agent(
    model=None,
    structured_output_model: type | None = None,
    hooks: list | None = None,
) -> Agent:
    """Create and return the configured Paperwork Agent.

    Args:
        model: Optional custom Model instance. If not provided, creates provider from env.
        structured_output_model: Optional Pydantic model for default structured output.
        hooks: Optional list of HookProvider instances. Attaches SafeAgentObservabilityHook by default.
    """
    if model is None:
        model = _create_model()

    if hooks is None:
        hooks = [SafeAgentObservabilityHook()]
    else:
        hooks = list(hooks)
        if not any(isinstance(h, SafeAgentObservabilityHook) for h in hooks):
            hooks.append(SafeAgentObservabilityHook())

    agent = Agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        tools=ALL_TOOLS,
        structured_output_model=structured_output_model,
        hooks=hooks,
    )

    return agent


def assess_paperwork(
    goal: str,
    agent: Agent | None = None,
):
    """Run the paperwork agent on a goal and return the validated ReadinessAssessment.

    Supports native structured output tool calls, fallback JSON text extraction,
    and graceful deterministic pipeline execution.

    Args:
        goal: The user's paperwork goal or instructions.
        agent: Optional existing Agent instance.

    Returns:
        ReadinessAssessment: Validated Pydantic structured output model.
    """
    import json
    import re
    from app.schemas import ReadinessAssessment

    provider = os.environ.get("MODEL_PROVIDER", "openai").lower()

    if agent is None:
        agent = create_agent()

    try:

        result = agent(goal, structured_output_model=ReadinessAssessment)
        if getattr(result, "structured_output", None) is not None:
            return result.structured_output

        # Check if result contains JSON string in its text response
        raw_text = getattr(result, "message", "") or str(result)
        json_match = re.search(r"\{.*\}", raw_text, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group(0))
                # Handle parameter wrapping if model formatted as tool call dictionary
                if "parameters" in data:
                    data = data["parameters"]
                return ReadinessAssessment.model_validate(data)
            except Exception:
                pass
    except Exception as e:
        logger.info(
            f"Agent structured output not directly produced ({e}). Executing deterministic verification engine."
        )

    # Fallback to the reliable deterministic verification engine
    return assess_paperwork_deterministic(goal)



class WorkflowNotFoundError(Exception):
    """Raised when a user goal cannot be matched to any available workflow."""
    pass


def assess_paperwork_deterministic(goal: str):
    """Execute the deterministic paperwork assessment pipeline.

    Used when no live LLM model API key is configured or for deterministic validation.
    Performs workflow discovery, requirement loading, document discovery, targeted
    fact extraction, and authoritative deterministic verification.

    Args:
        goal: The user's natural language goal (e.g. 'I want to complete the example application.').

    Returns:
        ReadinessAssessment: Validated Pydantic structured output model.

    Raises:
        WorkflowNotFoundError: If no matching workflow can be identified for the goal.
    """
    import json
    from app.schemas import ReadinessAssessment

    # 1. Discover target workflow
    discovery_raw = discover_workflow._tool_func(user_goal=goal)
    discovery = json.loads(discovery_raw)
    if discovery.get("status") == "workflow_not_found":
        raise WorkflowNotFoundError(
            discovery.get("message", f"No workflow could be identified for goal: '{goal}'")
        )

    workflow_id = discovery["workflow_id"]

    # 2. Load requirements
    wf_raw = get_workflow_requirements._tool_func(workflow_id=workflow_id)
    wf_data = json.loads(wf_raw)
    requirements = wf_data.get("requirements", [])

    # 3. Discover available documents
    docs_raw = list_documents._tool_func()
    docs_data = json.loads(docs_raw)
    available_docs = docs_data.get("documents", [])

    # 4. Extract facts with provenance across documents
    # Dynamically gather all fields declared across requirements
    all_req_fields = set()
    for req in requirements:
        for f in req.get("relevant_fields", []):
            if f and f != "photograph":
                all_req_fields.add(f)

    # Standard universal administrative fields
    universal_fields = {
        "full_name", "date_of_birth", "address", "id_number", 
        "nationality", "qualification", "institution", "employer"
    }
    target_fields = sorted(all_req_fields.union(universal_fields))
    fields_str = ",".join(target_fields)

    all_facts = []
    for doc in available_docs:
        doc_id = doc["document_id"]
        facts_raw = extract_document_facts._tool_func(document_id=doc_id, requested_fields=fields_str)
        facts_data = json.loads(facts_raw)
        for fact in facts_data.get("extracted_facts", []):
            if fact.get("value"):
                all_facts.append(fact)


    # 5. Authoritative deterministic verification
    assessment_raw = verify_requirements._tool_func(
        workflow_id=workflow_id,
        evidence_json=json.dumps(all_facts),
    )
    return ReadinessAssessment.model_validate_json(assessment_raw)
