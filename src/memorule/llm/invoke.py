"""Structured LLM invocation with automatic fallback."""

from __future__ import annotations

import json
from typing import TypeVar

from pydantic import BaseModel

from memorule.config import StructuredOutputMode
from memorule.exceptions import ConfigError
from memorule.prompts.parsing import parse_llm_response
from memorule.protocols import LanguageModel, StructuredLanguageModel

T = TypeVar("T", bound=BaseModel)


def format_schema_hint(response_model: type[BaseModel]) -> str:
    schema = json.dumps(response_model.model_json_schema(), indent=2)
    return (
        "\n\nRespond with valid JSON only, no markdown fences or extra text. "
        f"Match this schema:\n{schema}"
    )


def _use_native_structured(llm: LanguageModel, mode: StructuredOutputMode) -> bool:
    if mode is StructuredOutputMode.NEVER:
        return False
    if mode is StructuredOutputMode.ALWAYS:
        if not isinstance(llm, StructuredLanguageModel):
            raise ConfigError(
                "structured_output is 'always' but the LanguageModel does not implement "
                "complete_structured(). Implement StructuredLanguageModel or set "
                "structured_output to 'auto' or 'never'."
            )
        return True
    return isinstance(llm, StructuredLanguageModel)


async def invoke_structured(
    llm: LanguageModel,
    prompt: str,
    *,
    response_model: type[T],
    system: str | None,
    stage: str,
    mode: StructuredOutputMode,
) -> T:
    if _use_native_structured(llm, mode):
        assert isinstance(llm, StructuredLanguageModel)
        return await llm.complete_structured(
            prompt,
            system=system,
            response_model=response_model,
        )

    fallback_prompt = prompt + format_schema_hint(response_model)
    raw = await llm.complete(fallback_prompt, system=system)
    return parse_llm_response(raw, response_model, stage=stage)
