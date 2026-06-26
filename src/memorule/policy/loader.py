"""Load policy configuration from YAML."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from memorule.exceptions import ConfigError
from memorule.policy.config import PolicyConfig


def load_policy(path: str | Path) -> PolicyConfig:
    policy_path = Path(path)
    if not policy_path.exists():
        raise ConfigError(f"Policy file not found: {policy_path}")

    with policy_path.open(encoding="utf-8") as f:
        raw: Any = yaml.safe_load(f)

    if not isinstance(raw, dict):
        raise ConfigError(f"Policy file must contain a YAML mapping: {policy_path}")

    try:
        return PolicyConfig.model_validate(raw)
    except Exception as exc:
        raise ConfigError(f"Invalid policy configuration in {policy_path}: {exc}") from exc
