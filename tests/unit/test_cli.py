"""Tests for CLI scaffolding and validation."""

from __future__ import annotations

import json

from memorule.cli.init import run_init
from memorule.cli.policy_wizard import run_wizard
from memorule.cli.validate import run_validate


def test_init_scaffolds_artifacts(tmp_path):
    target = tmp_path / "memorule"
    msg = run_init(str(target))
    assert "Next steps" in msg
    assert (target / "memorule.yaml").exists()
    assert (target / "policy" / "policy.yaml").exists()
    assert (target / "providers" / "llm.py.example").exists()
    assert (target / "providers" / "embeddings.py.example").exists()
    assert (target / "providers" / "stores.py.example").exists()
    assert (target / "hooks" / "example_auditor.py").exists()

    from memorule.config import load_config
    from memorule.policy.loader import load_policy

    config = load_config(target / "memorule.yaml")
    assert "memory orchestration assistant" in config.prompts.system
    assert "memory_extraction" in config.prompts.stages
    assert config.prompts.structured_output.value == "auto"

    policy = load_policy(target / "policy" / "policy.yaml")
    assert policy.extraction is not None
    assert "project" in policy.memory_policy.create_when.lower()
    assert "chicken" not in policy.memory_policy.create_when.lower()


def test_init_refuses_nonempty_without_force(tmp_path):
    target = tmp_path / "memorule"
    run_init(str(target))
    msg = run_init(str(target))
    assert "already exists" in msg


def test_init_force_overwrites(tmp_path):
    target = tmp_path / "memorule"
    run_init(str(target))
    msg = run_init(str(target), force=True)
    assert "Next steps" in msg


def test_validate_after_init(tmp_path):
    target = tmp_path / "memorule"
    run_init(str(target))
    ok, messages = run_validate(str(target / "memorule.yaml"))
    assert ok is True
    assert any("policy" in m for m in messages)


def test_validate_missing_config(tmp_path):
    ok, messages = run_validate(str(tmp_path / "nope.yaml"))
    assert ok is False
    assert "ERROR" in messages[0]


def test_wizard_non_interactive(tmp_path):
    answers = tmp_path / "answers.json"
    answers.write_text(json.dumps({
        "create_when": "store preferences",
        "discard_when": "ignore greetings",
        "deduplication": "merge dupes",
        "reconciliation": "prefer newer",
    }))
    policy_path = tmp_path / "policy.yaml"
    msg = run_wizard(str(policy_path), non_interactive=str(answers))
    assert "written" in msg

    from memorule.policy.loader import load_policy

    policy = load_policy(policy_path)
    assert policy.memory_policy.create_when == "store preferences"
    assert policy.deduplication.rules == "merge dupes"


def test_wizard_interactive(tmp_path):
    policy_path = tmp_path / "policy.yaml"
    answers = iter([
        "store prefs",
        "ignore chit chat",
        "merge dupes",
        "prefer newer",
        "",  # skip extraction
        "",  # skip retrieval
    ])
    run_wizard(str(policy_path), prompt_fn=lambda _: next(answers))

    from memorule.policy.loader import load_policy

    policy = load_policy(policy_path)
    assert policy.memory_policy.discard_when == "ignore chit chat"
    assert policy.retrieval is None
