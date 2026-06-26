"""`memorule validate` — validate config and policy without running the pipeline."""

from __future__ import annotations

import importlib
from pathlib import Path

from memorule.config import load_config
from memorule.exceptions import ConfigError
from memorule.policy.loader import load_policy


def run_validate(
    config_path: str = "memorule/memorule.yaml",
    *,
    check_providers: bool = False,
) -> tuple[bool, list[str]]:
    messages: list[str] = []
    ok = True

    config_file = Path(config_path)
    try:
        config = load_config(config_file)
        messages.append(f"OK: config '{config_file}' is valid")
    except ConfigError as exc:
        return False, [f"ERROR: {exc}"]

    policy_path = config.resolve_policy_path(config_file.parent)
    try:
        policy = load_policy(policy_path)
        messages.append(f"OK: policy '{policy_path}' is valid")
    except ConfigError as exc:
        ok = False
        messages.append(f"ERROR: {exc}")
        return ok, messages

    for name in ("memory_policy", "deduplication", "reconciliation"):
        if getattr(policy, name, None) is None:
            ok = False
            messages.append(f"ERROR: required policy section '{name}' is missing")

    if check_providers:
        for label, spec in config.providers.model_dump().items():
            module_path, _, attr = spec.partition(":")
            try:
                module = importlib.import_module(module_path)
                if attr and not hasattr(module, attr):
                    ok = False
                    messages.append(f"ERROR: provider '{label}' missing attribute '{attr}'")
                else:
                    messages.append(f"OK: provider '{label}' importable")
            except ImportError as exc:
                ok = False
                messages.append(f"ERROR: provider '{label}' not importable: {exc}")

    return ok, messages
