"""Pipeline execution context."""

from __future__ import annotations

from dataclasses import dataclass, field

from memorule.policy.config import PolicyConfig
from memorule.protocols import EmbeddingModel, LanguageModel, MemoryStore, VectorStore
from memorule.types import (
    ExplainabilityTrace,
    Interaction,
    Memory,
    MemoryDecision,
    SimilarMemory,
)


@dataclass
class PipelineContext:
    interaction: Interaction
    policy: PolicyConfig
    llm: LanguageModel
    embeddings: EmbeddingModel
    vector_store: VectorStore
    memory_store: MemoryStore

    decision: MemoryDecision | None = None
    reason: str | None = None
    matched_policy: str | None = None
    memory: Memory | None = None
    candidates: list[SimilarMemory] = field(default_factory=list)
    embedding: list[float] | None = None
    target_memory_id: str | None = None
    trace: ExplainabilityTrace = field(default_factory=ExplainabilityTrace)
    halt: bool = False
