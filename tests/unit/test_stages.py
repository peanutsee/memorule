"""Unit tests for individual pipeline stages."""

from __future__ import annotations

from memorule.pipeline.context import PipelineContext
from memorule.pipeline.stages import (
    ConflictResolutionStage,
    DeduplicationStage,
    EmbeddingGenerationStage,
    MemoryExtractionStage,
    MetadataEnrichmentStage,
    PersistenceStage,
    PolicyEvaluationStage,
    SimilaritySearchStage,
)
from memorule.policy.config import PolicyConfig, RulesSection
from memorule.types import Interaction, Memory, MemoryDecision, SimilarMemory


def make_ctx(llm, embeddings, vector_store, memory_store, policy, content="hello"):
    return PipelineContext(
        interaction=Interaction(content=content),
        policy=policy,
        llm=llm,
        embeddings=embeddings,
        vector_store=vector_store,
        memory_store=memory_store,
    )


async def test_policy_evaluation_store(llm, embeddings, vector_store, memory_store, policy):
    llm.set("Evaluate whether", {"decision": "store", "reason": "pref", "matched_policy": "prefs"})
    ctx = make_ctx(llm, embeddings, vector_store, memory_store, policy)
    ctx = await PolicyEvaluationStage().run(ctx)
    assert ctx.decision is MemoryDecision.STORE
    assert ctx.halt is False


async def test_policy_evaluation_discard(llm, embeddings, vector_store, memory_store, policy):
    llm.set("Evaluate whether", {"decision": "discard", "reason": "greeting", "matched_policy": "x"})
    ctx = make_ctx(llm, embeddings, vector_store, memory_store, policy)
    ctx = await PolicyEvaluationStage().run(ctx)
    assert ctx.decision is MemoryDecision.DISCARD
    assert ctx.halt is True


async def test_memory_extraction(llm, embeddings, vector_store, memory_store, policy):
    llm.set(
        "Extract a structured",
        {"type": "preference", "content": "User prefers dark mode", "summary": "dark", "confidence": 0.9},
    )
    ctx = make_ctx(llm, embeddings, vector_store, memory_store, policy)
    ctx = await MemoryExtractionStage().run(ctx)
    assert ctx.memory is not None
    assert ctx.memory.type == "preference"
    assert ctx.memory.confidence == 0.9


async def test_metadata_enrichment_skips_without_rules(
    llm, embeddings, vector_store, memory_store, policy
):
    ctx = make_ctx(llm, embeddings, vector_store, memory_store, policy)
    ctx.memory = Memory(content="x")
    ctx = await MetadataEnrichmentStage().run(ctx)
    assert ctx.trace.steps[-1].decision == "skipped"


async def test_metadata_enrichment_applies(llm, embeddings, vector_store, memory_store):
    policy = PolicyConfig.default()
    policy.metadata_enrichment = RulesSection(rules="tag things")
    llm.set(
        "Enrich this memory",
        {"tags": ["ui"], "category": "preference", "metadata": {"k": "v"}, "reason": "ok"},
    )
    ctx = make_ctx(llm, embeddings, vector_store, memory_store, policy)
    ctx.memory = Memory(content="x")
    ctx = await MetadataEnrichmentStage().run(ctx)
    assert ctx.memory.metadata["tags"] == ["ui"]
    assert ctx.memory.metadata["category"] == "preference"
    assert ctx.memory.metadata["k"] == "v"


async def test_embedding_generation(llm, embeddings, vector_store, memory_store, policy):
    ctx = make_ctx(llm, embeddings, vector_store, memory_store, policy)
    ctx.memory = Memory(content="x")
    ctx = await EmbeddingGenerationStage().run(ctx)
    assert ctx.embedding is not None
    assert len(ctx.embedding) == embeddings.dim


async def test_similarity_search_finds_candidates(
    llm, embeddings, vector_store, memory_store, policy
):
    existing = Memory(id="m1", content="User likes dark mode")
    await memory_store.save(existing)
    await vector_store.upsert("m1", await embeddings.embed("User likes dark mode"), {})
    ctx = make_ctx(llm, embeddings, vector_store, memory_store, policy)
    ctx.memory = Memory(content="User likes dark mode")
    ctx.embedding = await embeddings.embed("User likes dark mode")
    ctx = await SimilaritySearchStage().run(ctx)
    assert len(ctx.candidates) == 1
    assert ctx.candidates[0].memory.id == "m1"


async def test_deduplication_new_when_no_candidates(
    llm, embeddings, vector_store, memory_store, policy
):
    ctx = make_ctx(llm, embeddings, vector_store, memory_store, policy)
    ctx.memory = Memory(content="x")
    ctx = await DeduplicationStage().run(ctx)
    assert ctx.trace.steps[-1].decision == "new"


async def test_deduplication_merge(llm, embeddings, vector_store, memory_store, policy):
    llm.set("Determine whether", {"action": "merge", "target_memory_id": "m1", "reason": "same"})
    ctx = make_ctx(llm, embeddings, vector_store, memory_store, policy)
    ctx.memory = Memory(content="x")
    ctx.candidates = [SimilarMemory(memory=Memory(id="m1", content="y"), similarity=0.9)]
    ctx = await DeduplicationStage().run(ctx)
    assert ctx.decision is MemoryDecision.MERGE
    assert ctx.target_memory_id == "m1"


async def test_conflict_resolution_version(llm, embeddings, vector_store, memory_store, policy):
    existing = Memory(id="m1", content="User prefers Python", version=1)
    await memory_store.save(existing)
    llm.set(
        "Reconcile conflicting",
        {
            "action": "version",
            "reason": "switched languages",
            "updated_content": "User develops in Rust",
            "updated_summary": "Rust",
        },
    )
    ctx = make_ctx(llm, embeddings, vector_store, memory_store, policy)
    ctx.memory = Memory(content="User develops in Rust")
    ctx.decision = MemoryDecision.MERGE
    ctx.target_memory_id = "m1"
    ctx = await ConflictResolutionStage().run(ctx)
    assert ctx.decision is MemoryDecision.VERSION
    assert ctx.memory.version == 2
    assert ctx.memory.content == "User develops in Rust"
    assert len(ctx.memory.metadata["version_history"]) == 1


async def test_persistence_saves_new(llm, embeddings, vector_store, memory_store, policy):
    ctx = make_ctx(llm, embeddings, vector_store, memory_store, policy)
    ctx.memory = Memory(id="m1", content="x")
    ctx.embedding = await embeddings.embed("x")
    ctx.decision = MemoryDecision.STORE
    ctx = await PersistenceStage().run(ctx)
    assert "m1" in memory_store.memories
    assert "m1" in vector_store.vectors
