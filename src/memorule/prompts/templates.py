"""Stage prompt builders and LLM response models."""

from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from memorule.policy.config import PolicyConfig
from memorule.types import Interaction, Memory, SimilarMemory

SYSTEM_PROMPT = (
    "You are a memory orchestration assistant. "
    "Preserve every specific entity the user stated; do not generalize or replace "
    "concrete details with broad categories. "
    "Respond with valid JSON only, no markdown fences or extra text."
)


def coerce_to_str(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def format_interaction_for_policy(interaction: Interaction) -> str:
    """Format interaction for store/discard evaluation (user statements primary)."""
    if interaction.user_content is not None:
        parts = [f"User (evaluate for long-term memory):\n{interaction.user_content}"]
        if interaction.assistant_content:
            parts.append(
                f"Assistant (context only — do not treat as user preference):\n"
                f"{interaction.assistant_content}"
            )
        return "\n\n".join(parts)
    return interaction.content


def format_interaction_for_extraction(interaction: Interaction) -> str:
    """Format interaction for memory extraction with labeled User/Assistant blocks."""
    if interaction.user_content is not None:
        parts = [f"User:\n{interaction.user_content}"]
        if interaction.assistant_content:
            parts.append(f"Assistant:\n{interaction.assistant_content}")
        return "\n\n".join(parts)
    return interaction.content


class PolicyEvaluationResponse(BaseModel):
    decision: Literal["store", "discard"]
    reason: str
    matched_policy: str


def format_memory_type_line(memory_type: str | None) -> str:
    if memory_type is None:
        return ""
    return f"Type: {memory_type}\n"


class ExtractionResponse(BaseModel):
    type: str | None = None
    content: str
    summary: str
    confidence: float = Field(ge=0.0, le=1.0)

    @field_validator("content", mode="before")
    @classmethod
    def _coerce_content(cls, value: Any) -> str:
        return coerce_to_str(value)


class MetadataEnrichmentResponse(BaseModel):
    tags: list[str] = Field(default_factory=list)
    category: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    reason: str


class DeduplicationResponse(BaseModel):
    action: Literal["new", "merge", "enrich"]
    target_memory_id: str | None = None
    reason: str


class ReconciliationResponse(BaseModel):
    action: Literal["update", "version", "keep_existing"]
    reason: str
    updated_content: str | None = None
    updated_summary: str | None = None

    @field_validator("updated_content", mode="before")
    @classmethod
    def _coerce_updated_content(cls, value: Any) -> str | None:
        if value is None:
            return None
        return coerce_to_str(value)


class RetrievalRerankResponse(BaseModel):
    memory_ids: list[str]
    reason: str


def build_policy_evaluation_prompt(interaction: Interaction, policy: PolicyConfig) -> str:
    formatted = format_interaction_for_policy(interaction)
    return f"""Evaluate whether this interaction should become a long-term memory.

Focus on what the USER stated. Assistant text is context only and must not cause a discard
when the user revealed a preference, fact, or other long-term information.

Store brief follow-up fragments that refine earlier context (e.g. "Actually use Rust for
the backend" after discussing a project — store it).

Create when:
{policy.memory_policy.create_when}

Discard when:
{policy.memory_policy.discard_when}

Examples:
- STORE: User says "I prefer dark mode" or "Actually use Rust for the backend"
- DISCARD: User says "hi" or "thanks!" with no lasting information

Interaction:
{formatted}

Respond with JSON:
{{"decision": "store"|"discard", "reason": "...", "matched_policy": "..."}}"""


def build_extraction_prompt(
    interaction: Interaction,
    policy: PolicyConfig,
    candidates: list[SimilarMemory] | None = None,
) -> str:
    formatted = format_interaction_for_extraction(interaction)
    extraction_rules = (
        policy.extraction.rules
        if policy.extraction is not None
        else (
            "Preserve every specific entity the user stated. Never replace specifics with "
            "generic categories."
        )
    )

    candidate_block = ""
    if candidates:
        lines = [
            "- ID: {id}, Summary: {summary}, Content: {content}".format(
                id=c.memory.id,
                summary=c.memory.summary or "(none)",
                content=c.memory.content,
            )
            for c in candidates
        ]
        candidate_block = f"""
Related existing memories (if this turn refines one, merge specifics into content):
{chr(10).join(lines)}
"""

    return f"""Extract a structured memory from this interaction.

What to store (from policy):
{policy.memory_policy.create_when}

Extraction rules:
{extraction_rules}

Field rules:
- "content": complete faithful prose with ALL user-stated specifics (names, dates, numbers,
  tools, projects, constraints). Never use a nested JSON object or array.
- "summary": specific retrieval label (max ~12 words) naming the concrete subject with key
  nouns — NOT a broad category like "user preference".
- "type": optional short free-form label (1–3 words) only when it aids retrieval
  (e.g. "work", "settings"); use null if a label adds no value. Not a fixed category taxonomy.
- Base the memory on USER statements; assistant text is context only.

Example for User: "I prefer dark mode in all my apps" / "Actually use Rust for the backend":
{{"type": "settings", "content": "User prefers dark mode in all apps and uses Rust for the backend", "summary": "dark mode and Rust backend", "confidence": 0.9}}
{candidate_block}
Interaction:
{formatted}

Respond with JSON:
{{"type": "..." or null, "content": "...", "summary": "...", "confidence": 0.0-1.0}}"""


def build_metadata_enrichment_prompt(memory: Memory, rules: str) -> str:
    return f"""Enrich this memory with metadata according to the rules.

Rules:
{rules}

Memory:
{format_memory_type_line(memory.type)}Content: {memory.content}
Summary: {memory.summary}

Respond with JSON:
{{"tags": ["..."], "category": "...", "metadata": {{}}, "reason": "..."}}"""


def build_deduplication_prompt(
    memory: Memory, candidates: list[SimilarMemory], rules: str
) -> str:
    candidate_text = "\n".join(
        f"- ID: {c.memory.id}, Summary: {c.memory.summary or '(none)'}, "
        f"Content: {c.memory.content}, Similarity: {c.similarity:.2f}"
        for c in candidates
    ) or "No similar memories found."
    return f"""Determine whether this new memory is a duplicate of existing memories.

Prefer "enrich" over "new" when memories cover the same topic or subject.
When enriching, the later reconciliation step will merge specifics.

Rules:
{rules}

New memory:
{format_memory_type_line(memory.type)}Summary: {memory.summary}
Content: {memory.content}

Existing candidates:
{candidate_text}

Respond with JSON:
{{"action": "new"|"merge"|"enrich", "target_memory_id": "..." or null, "reason": "..."}}"""


def build_reconciliation_prompt(
    new_memory: Memory, existing: Memory, rules: str
) -> str:
    return f"""Reconcile conflicting or overlapping memories according to the rules.

When updating or versioning, merged content and summary must retain ALL specifics from
both memories. Never replace a specific memory with a generic one.

Rules:
{rules}

New memory:
Content: {new_memory.content}
Summary: {new_memory.summary}

Existing memory (ID: {existing.id}):
Content: {existing.content}
Summary: {existing.summary}
Version: {existing.version}

Respond with JSON:
{{"action": "update"|"version"|"keep_existing", "reason": "...", "updated_content": "..." or null, "updated_summary": "..." or null}}"""


def build_retrieval_rerank_prompt(
    query: str, memories: list[Memory], rules: str
) -> str:
    memory_text = "\n".join(
        f"- ID: {m.id}, {f'Type: {m.type}, ' if m.type else ''}"
        f"Content: {m.content}, Confidence: {m.confidence}"
        for m in memories
    )
    return f"""Rank and filter memories by relevance to the query.

Rules:
{rules}

Query:
{query}

Candidate memories:
{memory_text}

Respond with JSON:
{{"memory_ids": ["id1", "id2", ...], "reason": "..."}}"""


def serialize_memories(memories: list[Memory]) -> str:
    return json.dumps([m.model_dump(mode="json") for m in memories], indent=2)
