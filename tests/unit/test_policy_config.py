"""Unit tests for policy and config loaders."""

from __future__ import annotations

import pytest

from memorule.config import load_config
from memorule.exceptions import ConfigError
from memorule.policy.config import PolicyConfig
from memorule.policy.loader import load_policy

POLICY_YAML = """
memory_policy:
  create_when: "store important things"
  discard_when: "ignore chit chat"
deduplication:
  rules: "merge duplicates"
reconciliation:
  rules: "prefer newer"
"""

CONFIG_YAML = """
policy_path: policy/policy.yaml
retrieval:
  limit: 5
  min_confidence: 0.3
context:
  format: xml
  max_memories: 4
"""


def test_load_policy(tmp_path):
    p = tmp_path / "policy.yaml"
    p.write_text(POLICY_YAML)
    policy = load_policy(p)
    assert policy.memory_policy.create_when == "store important things"
    assert policy.deduplication.rules == "merge duplicates"
    assert policy.metadata_enrichment is None


def test_load_policy_missing_file(tmp_path):
    with pytest.raises(ConfigError):
        load_policy(tmp_path / "nope.yaml")


def test_load_policy_invalid(tmp_path):
    p = tmp_path / "bad.yaml"
    p.write_text("memory_policy:\n  create_when: only_create\n")
    with pytest.raises(ConfigError):
        load_policy(p)


def test_policy_default():
    policy = PolicyConfig.default()
    assert "long-term" in policy.memory_policy.create_when


def test_load_config(tmp_path):
    c = tmp_path / "memorule.yaml"
    c.write_text(CONFIG_YAML)
    config = load_config(c)
    assert config.retrieval.limit == 5
    assert config.context.format.value == "xml"
    assert config.context.max_memories == 4


def test_resolve_policy_path(tmp_path):
    c = tmp_path / "memorule.yaml"
    c.write_text(CONFIG_YAML)
    config = load_config(c)
    resolved = config.resolve_policy_path(tmp_path)
    assert resolved == tmp_path / "policy/policy.yaml"
