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
    metadata_enrichment: RulesSection | None = None
    retrieval: RulesSection | None = None

    @classmethod
    def default(cls) -> PolicyConfig:
        return cls(
            memory_policy=MemoryPolicySection(
                create_when=(
                    "Store memories when an interaction reveals long-term user preferences, "
                    "ongoing projects, recurring facts, commitments, relationships, "
                    "or information that will likely be useful in future conversations."
                ),
                discard_when=(
                    "Ignore greetings, temporary requests, jokes, casual conversation, "
                    "and one-off questions."
                ),
            ),
            deduplication=RulesSection(
                rules=(
                    "If two memories describe the same long-term fact, merge them. "
                    "If the new interaction adds additional details, enrich the existing memory. "
                    "Preserve useful metadata. Avoid duplicate entries."
                ),
            ),
            reconciliation=RulesSection(
                rules=(
                    "If new information contradicts an existing memory, prefer newer information. "
                    "Preserve previous values in version history. Record when the change occurred."
                ),
            ),
        )
