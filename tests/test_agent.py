"""Tests for the Strands Paperwork Agent setup and live agent paths.

Run with: python -m pytest tests/test_agent.py -v
"""

from __future__ import annotations

import os
from typing import Any
from unittest.mock import patch

import pytest
from pydantic import BaseModel
from strands import Agent
from strands.models import Model

from app.agent import ALL_TOOLS, create_agent, assess_paperwork
from app.prompts import SYSTEM_PROMPT
from app.schemas import (
    ConflictDetail,
    DocumentFact,
    ReadinessAssessment,
    RequirementCheck,
    RequirementStatus,
)


class DummyModel(Model):
    """Minimal Model implementation for testing agent orchestration without external APIs."""

    def __init__(self, name: str = "dummy"):
        self.name = name

    def update_config(self, **kwargs: Any) -> None:
        pass

    def get_config(self) -> dict:
        return {"model_id": self.name}

    async def stream(self, messages: Any, **kwargs: Any):
        if False:
            yield

    async def structured_output(self, output_model: Any, prompt: Any, **kwargs: Any):
        if False:
            yield


class TestAgentConfiguration:
    """Tests for agent initialization and environment configuration."""

    def test_missing_openai_key_raises_value_error(self):
        with patch.dict(os.environ, {"MODEL_PROVIDER": "openai", "OPENAI_API_KEY": ""}, clear=False):
            with pytest.raises(ValueError, match="OPENAI_API_KEY is not set"):
                create_agent()

    def test_missing_anthropic_key_raises_value_error(self):
        with patch.dict(os.environ, {"MODEL_PROVIDER": "anthropic", "ANTHROPIC_API_KEY": ""}, clear=False):
            with pytest.raises(ValueError, match="ANTHROPIC_API_KEY is not set"):
                create_agent()

    def test_invalid_provider_raises_value_error(self):
        with patch.dict(os.environ, {"MODEL_PROVIDER": "unsupported_provider"}, clear=False):
            with pytest.raises(ValueError, match="Unsupported MODEL_PROVIDER"):
                create_agent()

    def test_assess_paperwork_missing_credentials_raises(self):
        with patch.dict(os.environ, {"MODEL_PROVIDER": "openai", "OPENAI_API_KEY": ""}, clear=False):
            with pytest.raises(ValueError, match="OPENAI_API_KEY is not set"):
                assess_paperwork("complete example application")

    def test_create_agent_with_injected_model(self):
        dummy = DummyModel()
        agent = create_agent(model=dummy)
        assert isinstance(agent, Agent)
        assert agent.system_prompt == SYSTEM_PROMPT

    def test_agent_has_all_intended_tools(self):
        dummy = DummyModel()
        agent = create_agent(model=dummy)

        expected_tools = {
            "discover_workflow",
            "get_workflow_requirements",
            "list_documents",
            "search_documents",
            "read_document",
            "extract_document_facts",
            "verify_requirements",
        }
        registered_tools = set(agent.tool_registry.registry.keys())
        assert expected_tools.issubset(registered_tools), (
            f"Missing tools: {expected_tools - registered_tools}"
        )
        assert len(registered_tools) == 7

    def test_agent_structured_output_model_registration(self):
        dummy = DummyModel()
        agent = create_agent(model=dummy, structured_output_model=ReadinessAssessment)
        assert agent._default_structured_output_model == ReadinessAssessment


class TestStructuredOutputCompatibility:
    """Tests confirming the ReadinessAssessment and EvidenceBundle schemas match Strands format."""

    def test_schema_generates_valid_json_schema(self):
        schema = ReadinessAssessment.model_json_schema()
        assert "properties" in schema
        assert "workflow_id" in schema["properties"]
        assert "ready" in schema["properties"]
        assert "completion_percentage" in schema["properties"]
        assert "satisfied_requirements" in schema["properties"]
        assert "missing_requirements" in schema["properties"]
        assert "conflicts" in schema["properties"]
        assert "recommended_next_actions" in schema["properties"]

    def test_evidence_bundle_schema(self):
        from app.schemas import EvidenceBundle

        fact = DocumentFact(
            field="full_name",
            value="Jane Alexandra Doe",
            source_document="doc_identity",
            confidence="high",
            evidence_snippet="Full Name: Jane Alexandra Doe",
        )
        bundle = EvidenceBundle(
            workflow_id="example_application",
            facts=[fact],
            source_documents=["doc_identity"],
            extraction_notes="Extracted from identity card",
        )
        assert bundle.workflow_id == "example_application"
        assert len(bundle.facts) == 1
        assert bundle.facts[0].field == "full_name"

        # Check JSON roundtrip
        json_str = bundle.model_dump_json()
        restored = EvidenceBundle.model_validate_json(json_str)
        assert restored.workflow_id == "example_application"
        assert restored.facts[0].value == "Jane Alexandra Doe"

    def test_workflow_discovery_result_schema(self):
        from app.schemas import WorkflowDiscoveryResult

        res = WorkflowDiscoveryResult(
            status="found",
            workflow_id="example_application",
            workflow_name="Example Government Application",
            confidence=0.95,
            reason="Matched goal keywords",
        )
        assert res.status == "found"
        assert res.confidence == 0.95

        not_found = WorkflowDiscoveryResult(
            status="workflow_not_found",
            reason="No matching workflow",
            available_workflows=[{"workflow_id": "example_application", "workflow_name": "Example"}],
        )
        assert not_found.status == "workflow_not_found"
        assert len(not_found.available_workflows) == 1

    def test_schema_instantiation_and_serialization(self):
        fact = DocumentFact(
            field="date_of_birth",
            value="1995-03-15",
            source_document="e5e2a0af7af9",
            confidence="high",
            evidence_snippet="DOB: 1995-03-15",
        )
        conflict = ConflictDetail(
            field="date_of_birth",
            values=[
                {"source_document": "e5e2a0af7af9", "value": "1995-03-15"},
                {"source_document": "e5ace8c163fa", "value": "1995-03-16"},
            ],
        )
        check = RequirementCheck(
            requirement_id="req_dob",
            requirement_name="Date of Birth Verification",
            status=RequirementStatus.CONFLICT,
            evidence=[fact],
            conflicts=[conflict],
            notes="Conflicting values detected",
        )
        assessment = ReadinessAssessment(
            workflow_id="example_application",
            workflow_name="Example Government Application",
            ready=False,
            completion_percentage=50.0,
            conflicts=[check],
            recommended_next_actions=["Resolve conflicting values for date_of_birth"],
        )

        assert assessment.ready is False
        assert assessment.completion_percentage == 50.0
        assert len(assessment.conflicts) == 1
        assert assessment.conflicts[0].conflicts[0].field == "date_of_birth"

        # Validate round-trip JSON serialization
        json_data = assessment.model_dump_json()
        restored = ReadinessAssessment.model_validate_json(json_data)
        assert restored.workflow_id == assessment.workflow_id
        assert restored.ready == assessment.ready
