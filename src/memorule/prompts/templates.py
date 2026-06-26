"""Stage prompt builders and LLM response models."""

from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, Field

from memorule.policy.config import PolicyConfig
from memorule.types import Interaction, Memory, SimilarMemory

SYSTEM_PROMPT = (
    "You are a memory orchestration assistant. "
    "Respond with valid JSON only, no markdown fences or extra text."
)


class PolicyEvaluationResponse(BaseModel):
    decision: Literal["store", "discard"]
    reason: str
    matched_policy: str


class ExtractionResponse(BaseModel):
    type: str
    content: str
    summary: str
    confidence: float = Field(ge=0.0, le=1.0)


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


class RetrievalRerankResponse(BaseModel):
    memory_ids: list[str]
    reason: str


def build_policy_evaluation_prompt(interaction: Interaction, policy: PolicyConfig) -> str:
    return f"""Evaluate whether this interaction should become a long-term memory.

Create when:
{policy.memory_policy.create_when}

Discard when:
{policy.memory_policy.discard_when}

Interaction:
{interaction.content}

Respond with JSON:
{{"decision": "store"|"discard", "reason": "...", "matched_policy": "..."}}"""


def build_extraction_prompt(interaction: Interaction) -> str:
    return f"""Extract a structured memory from this interaction.

Interaction:
{interaction.content}

Respond with JSON:
{{"type": "preference|fact|project|commitment|relationship|other", "content": "...", "summary": "...", "confidence": 0.0-1.0}}"""


def build_metadata_enrichment_prompt(memory: Memory, rules: str) -> str:
    return f"""Enrich this memory with metadata according to the rules.

Rules:
{rules}

Memory:
Type: {memory.type}
Content: {memory.content}
Summary: {memory.summary}

Respond with JSON:
{{"tags": ["..."], "category": "...", "metadata": {{}}, "reason": "..."}}"""


def build_deduplication_prompt(
    memory: Memory, candidates: list[SimilarMemory], rules: str
) -> str:
    candidate_text = "\n".join(
        f"- ID: {c.memory.id}, Content: {c.memory.content}, Similarity: {c.similarity:.2f}"
        for c in candidates
    ) or "No similar memories found."
    return f"""Determine whether this new memory is a duplicate of existing memories.

Rules:
{rules}

New memory:
Type: {memory.type}
Content: {memory.content}

Existing candidates:
{candidate_text}

Respond with JSON:
{{"action": "new"|"merge"|"enrich", "target_memory_id": "..." or null, "reason": "..."}}"""


def build_reconciliation_prompt(
    new_memory: Memory, existing: Memory, rules: str
) -> str:
    return f"""Reconcile conflicting or overlapping memories according to the rules.

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
        f"- ID: {m.id}, Type: {m.type}, Content: {m.content}, Confidence: {m.confidence}"
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
