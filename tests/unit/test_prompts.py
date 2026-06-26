"""Unit tests for prompt builders and interaction formatters."""

from __future__ import annotations

from memorule.policy.config import PolicyConfig
from memorule.prompts.templates import (
    build_extraction_prompt,
    build_policy_evaluation_prompt,
    format_interaction_for_extraction,
    format_interaction_for_policy,
)
from memorule.types import Interaction, Memory, SimilarMemory


def test_format_interaction_for_policy_user_focus():
    interaction = Interaction(
        content="User: I like chicken rice\nAssistant: Here is a recipe...",
        user_content="I like chicken rice",
        assistant_content="Here is a recipe...",
    )
    formatted = format_interaction_for_policy(interaction)
    assert "User (evaluate for long-term memory)" in formatted
    assert "I like chicken rice" in formatted
    assert "Assistant (context only" in formatted
    assert "Here is a recipe" in formatted


def test_format_interaction_for_extraction_labeled_blocks():
    interaction = Interaction(
        content="User: With hot sauce!\nAssistant: Great choice!",
        user_content="With hot sauce!",
        assistant_content="Great choice!",
    )
    formatted = format_interaction_for_extraction(interaction)
    assert formatted.startswith("User:\nWith hot sauce!")
    assert "Assistant:\nGreat choice!" in formatted


def test_format_interaction_fallback_to_content():
    interaction = Interaction(content="plain message")
    assert format_interaction_for_policy(interaction) == "plain message"
    assert format_interaction_for_extraction(interaction) == "plain message"


def test_build_policy_evaluation_prompt_uses_user_focus():
    policy = PolicyConfig.default()
    interaction = Interaction(
        content="User: hi\nAssistant: long recipe",
        user_content="hi",
        assistant_content="long recipe",
    )
    prompt = build_policy_evaluation_prompt(interaction, policy)
    assert "Focus on what the USER stated" in prompt
    assert "User (evaluate for long-term memory)" in prompt


def test_build_extraction_prompt_includes_policy_and_rules():
    policy = PolicyConfig.default()
    interaction = Interaction(content="I like chicken rice", user_content="I like chicken rice")
    prompt = build_extraction_prompt(interaction, policy)
    assert "Extraction rules:" in prompt
    assert policy.memory_policy.create_when[:40] in prompt
    assert "NOT a broad category" in prompt
    assert "Hainanese chicken rice" in prompt


def test_build_extraction_prompt_includes_pre_extraction_candidates():
    policy = PolicyConfig.default()
    interaction = Interaction(content="With hot sauce!", user_content="With hot sauce!")
    candidates = [
        SimilarMemory(
            memory=Memory(
                id="m1",
                content="User likes chicken rice",
                summary="chicken rice",
            ),
            similarity=0.85,
        )
    ]
    prompt = build_extraction_prompt(interaction, policy, candidates)
    assert "Related existing memories" in prompt
    assert "m1" in prompt
    assert "chicken rice" in prompt
