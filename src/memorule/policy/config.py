"""Policy configuration models."""

from __future__ import annotations

from pydantic import BaseModel


class MemoryPolicySection(BaseModel):
    create_when: str
    discard_when: str


class RulesSection(BaseModel):
    rules: str


class PolicyConfig(BaseModel):
    memory_policy: MemoryPolicySection
    deduplication: RulesSection
    reconciliation: RulesSection
    extraction: RulesSection | None = None
    metadata_enrichment: RulesSection | None = None
    retrieval: RulesSection | None = None

    @classmethod
    def default(cls) -> PolicyConfig:
        return cls(
            memory_policy=MemoryPolicySection(
                create_when=(
                    "Store memories when an interaction reveals long-term user preferences "
                    "(including food, dishes, cuisines, sauces, condiments, and dietary "
                    "restrictions), ongoing projects, recurring facts, commitments, "
                    "relationships, or information that will likely be useful in future "
                    "conversations. Store even brief or follow-up preference mentions "
                    "(e.g. 'With hot sauce!') that refine earlier statements."
                ),
                discard_when=(
                    "Ignore pure greetings with no substantive content, temporary one-off "
                    "requests, jokes, and generic small talk with no lasting user facts. "
                    "Do not discard multi-turn discussions where the user states likes, "
                    "dislikes, or refinements to earlier preferences."
                ),
            ),
            extraction=RulesSection(
                rules=(
                    "Preserve every specific entity the user stated: dish names, cuisines, "
                    "cooking styles, sauces, brands, and likes/dislikes. Never replace "
                    "specifics with generic categories (e.g. do not write 'food preference' "
                    "when the user said 'chicken rice'). The summary must name the concrete "
                    "subject (e.g. 'Hainanese chicken rice with hot sauce'), not a broad "
                    "category."
                ),
            ),
            deduplication=RulesSection(
                rules=(
                    "If two memories describe the same long-term fact or the same topic, "
                    "merge or enrich them — do not create a duplicate. Preferences about the "
                    "same food, dish, or subject should be enriched into one memory. "
                    "If the new interaction adds additional details, enrich the existing "
                    "memory. Preserve useful metadata. Avoid duplicate entries."
                ),
            ),
            reconciliation=RulesSection(
                rules=(
                    "If new information contradicts an existing memory, prefer newer "
                    "information. When enriching, merged content and summary must retain "
                    "all specifics from both sides — never replace a specific memory with "
                    "a generic one. Preserve previous values in version history. Record "
                    "when the change occurred."
                ),
            ),
        )
