"""Unit tests for invoke_structured and PromptConfig."""

from __future__ import annotations

import json

import pytest

from memorule.config import PromptConfig, StructuredOutputMode, load_config
from memorule.exceptions import ConfigError
from memorule.llm.invoke import format_schema_hint, invoke_structured
from memorule.prompts.templates import PolicyEvaluationResponse
from memorule.protocols import StructuredLanguageModel


async def test_invoke_structured_fallback_appends_schema(llm):
    llm.set("Evaluate whether", {"decision": "store", "reason": "ok", "matched_policy": "x"})
    prompts = PromptConfig.default()
    prompts.structured_output = StructuredOutputMode.NEVER

    result = await invoke_structured(
        llm,
        "Evaluate whether to store this.",
        response_model=PolicyEvaluationResponse,
        system="system prompt",
        stage="policy_evaluation",
        mode=prompts.structured_output,
    )

    assert result.decision == "store"
    assert "Respond with valid JSON only" in llm.calls[0]
    assert "decision" in llm.calls[0]


async def test_invoke_structured_native_skips_schema_hint():
    class StructuredOnly:
        async def complete(self, prompt: str, *, system: str | None = None) -> str:
            raise AssertionError("complete should not be called")

        async def complete_structured(self, prompt, *, system=None, response_model):
            return response_model(
                decision="discard",
                reason="greeting",
                matched_policy="discard",
            )

    llm = StructuredOnly()
    assert isinstance(llm, StructuredLanguageModel)

    result = await invoke_structured(
        llm,
        "Evaluate whether",
        response_model=PolicyEvaluationResponse,
        system="sys",
        stage="policy_evaluation",
        mode=StructuredOutputMode.AUTO,
    )
    assert result.decision == "discard"


async def test_invoke_structured_always_without_provider_raises():
    class TextOnly:
        async def complete(self, prompt: str, *, system: str | None = None) -> str:
            return "{}"

    with pytest.raises(ConfigError, match="structured_output is 'always'"):
        await invoke_structured(
            TextOnly(),
            "prompt",
            response_model=PolicyEvaluationResponse,
            system=None,
            stage="policy_evaluation",
            mode=StructuredOutputMode.ALWAYS,
        )


async def test_invoke_structured_auto_uses_structured_provider():
    class StructuredLLM:
        used_native = False

        async def complete(self, prompt: str, *, system: str | None = None) -> str:
            return json.dumps({"decision": "store", "reason": "x", "matched_policy": "y"})

        async def complete_structured(self, prompt, *, system=None, response_model):
            StructuredLLM.used_native = True
            return response_model(decision="store", reason="native", matched_policy="z")

    llm = StructuredLLM()
    result = await invoke_structured(
        llm,
        "Evaluate whether",
        response_model=PolicyEvaluationResponse,
        system=None,
        stage="policy_evaluation",
        mode=StructuredOutputMode.AUTO,
    )
    assert StructuredLLM.used_native
    assert result.reason == "native"


def test_prompt_config_resolve_system_prompt():
    prompts = PromptConfig(
        system="Global system",
        stages={"policy_evaluation": "Stage-specific guidance."},
    )
    merged = prompts.resolve_system_prompt("policy_evaluation")
    assert merged.startswith("Global system")
    assert "Stage-specific guidance." in merged

    assert prompts.resolve_system_prompt("unknown_stage") == "Global system"


def test_prompt_config_load_from_yaml(tmp_path):
    config_path = tmp_path / "memorule.yaml"
    config_path.write_text(
        """
prompts:
  system: |
    Custom system persona.
  stages:
    memory_extraction: |
      Extract carefully.
  structured_output: never
"""
    )
    config = load_config(config_path)
    assert "Custom system persona" in config.prompts.system
    assert config.prompts.stages["memory_extraction"] == "Extract carefully.\n"
    assert config.prompts.structured_output is StructuredOutputMode.NEVER


def test_format_schema_hint_includes_model_fields():
    hint = format_schema_hint(PolicyEvaluationResponse)
    assert "Respond with valid JSON only" in hint
    assert "decision" in hint
