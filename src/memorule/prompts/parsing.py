"""JSON extraction and validation of LLM outputs."""

from __future__ import annotations

import json
import re
from typing import TypeVar

from pydantic import BaseModel

from memorule.exceptions import PolicyParseError

T = TypeVar("T", bound=BaseModel)

_FENCE_PATTERN = re.compile(r"```(?:json)?\s*\n?(.*?)\n?```", re.DOTALL | re.IGNORECASE)


def extract_json(text: str) -> str:
    text = text.strip()
    match = _FENCE_PATTERN.search(text)
    if match:
        return match.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]
    return text


def parse_llm_response(text: str, model: type[T], *, stage: str) -> T:
    raw = extract_json(text)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise PolicyParseError(
            f"Failed to parse JSON from LLM response in stage '{stage}': {exc}",
            raw_output=text,
            stage=stage,
        ) from exc

    try:
        return model.model_validate(data)
    except Exception as exc:
        raise PolicyParseError(
            f"Failed to validate LLM response in stage '{stage}': {exc}",
            raw_output=text,
            stage=stage,
        ) from exc
