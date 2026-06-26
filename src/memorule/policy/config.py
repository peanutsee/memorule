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
                    "Store memories when the user reveals information that should persist "
                    "across future conversations: preferences, constraints, ongoing projects "
                    "or tasks, decisions, commitments, stable facts about themselves or their "
                    "environment, and relationships to people, tools, or systems. Store "
                    "brief follow-ups that refine earlier statements (e.g. 'Actually use "
                    "PostgreSQL instead')."
                ),
                discard_when=(
                    "Ignore pure greetings or thanks with no new facts, one-off questions "
                    "with no lasting user information, jokes, and filler small talk. Do not "
                    "discard turns where the user adds or corrects long-term context."
                ),
            ),
            extraction=RulesSection(
                rules=(
                    "Preserve every specific entity the user stated: names, dates, numbers, "
                    "tools, projects, and constraints. Never replace specifics with generic "
                    "categories (e.g. do not write 'tech preference' when the user said "
                    "'Rust'). The summary must name the concrete subject (e.g. 'Rust backend "
                    "for API project'), not a broad category. The type field is optional; "
                    "use a short free-form label only when helpful, otherwise omit."
                ),
            ),
            deduplication=RulesSection(
                rules=(
                    "If two memories describe the same long-term fact or the same topic, "
                    "merge or enrich them — do not create a duplicate. Memories about the "
                    "same subject should be enriched into one memory. If the new interaction "
                    "adds additional details, enrich the existing memory. Preserve useful "
                    "metadata. Avoid duplicate entries."
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
