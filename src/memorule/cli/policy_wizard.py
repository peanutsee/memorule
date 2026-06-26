"""`memorule policy wizard` — interactive policy generation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

import yaml

_SECTIONS: dict[str, tuple[str, str]] = {
    "create_when": (
        "memory_policy",
        "What interactions should become long-term memories?",
    ),
    "discard_when": (
        "memory_policy",
        "What interactions should be ignored?",
    ),
    "deduplication": (
        "deduplication",
        "How should similar/duplicate memories be handled?",
    ),
    "reconciliation": (
        "reconciliation",
        "How should conflicting memories be resolved?",
    ),
    "extraction": (
        "extraction",
        "What specifics must be preserved when extracting memories? (optional, blank to skip)",
    ),
    "retrieval": (
        "retrieval",
        "Which memories are relevant for a given query? (optional, blank to skip)",
    ),
}


def _load_existing(path: Path) -> dict[str, Any]:
    if path.exists():
        with path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
            if isinstance(data, dict):
                return data
    return {}


def _apply_answer(policy: dict[str, Any], key: str, answer: str) -> None:
    if not answer.strip():
        return
    if key == "create_when":
        policy.setdefault("memory_policy", {})["create_when"] = answer
    elif key == "discard_when":
        policy.setdefault("memory_policy", {})["discard_when"] = answer
    else:
        policy[key] = {"rules": answer}


def run_wizard(
    policy_path: str = "memorule/policy/policy.yaml",
    *,
    section: str | None = None,
    non_interactive: str | None = None,
    prompt_fn: Callable[[str], str] = input,
) -> str:
    path = Path(policy_path)
    policy = _load_existing(path)

    if non_interactive is not None:
        with Path(non_interactive).open(encoding="utf-8") as f:
            answers = json.load(f)
        for key, answer in answers.items():
            if key in _SECTIONS:
                _apply_answer(policy, key, answer)
    else:
        keys = [section] if section else list(_SECTIONS)
        for key in keys:
            if key not in _SECTIONS:
                return f"Unknown section: {key}. Valid: {', '.join(_SECTIONS)}"
            _, question = _SECTIONS[key]
            answer = prompt_fn(f"\n{question}\n> ")
            _apply_answer(policy, key, answer)

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(policy, f, default_flow_style=False, sort_keys=False)

    return f"Policy written to {path}"
