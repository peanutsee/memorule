"""End-to-end pipeline integration tests."""

from __future__ import annotations

from memorule import (
    BaseStage,
    ContextBuilder,
    HookPoint,
    Interaction,
    MemoryEngine,
    MemorySession,
    RetrievalQuery,
)
from memorule.pipeline.context import PipelineContext
from memorule.policy.config import PolicyConfig, RulesSection
from memorule.types import ContextFormat, Memory, MemoryDecision


def make_engine(llm, embeddings, vector_store, memory_store, policy=None, **kwargs):
    return MemoryEngine(
        llm=llm,
        embeddings=embeddings,
        vector_store=vector_store,
        memory_store=memory_store,
        policy=policy or PolicyConfig.default(),
        **kwargs,
    )


async def test_store_path(llm, embeddings, vector_store, memory_store):
    llm.set("Evaluate whether", {"decision": "store", "reason": "long-term pref", "matched_policy": "prefs"})
    llm.set("Extract a structured", {"type": "preference", "content": "User prefers dark mode", "summary": "dark", "confidence": 0.94})
    engine = make_engine(llm, embeddings, vector_store, memory_store)

    result = await engine.process(Interaction(content="I prefer dark mode in all my apps."))

    assert result.decision is MemoryDecision.STORE
    assert result.memory is not None
    assert result.memory.content == "User prefers dark mode"
    assert result.confidence == 0.94
    assert len(memory_store.memories) == 1
    assert "policy_evaluation" in result.explanation.lower() or result.trace.steps


async def test_discard_path(llm, embeddings, vector_store, memory_store):
    llm.set("Evaluate whether", {"decision": "discard", "reason": "greeting", "matched_policy": "discard"})
    engine = make_engine(llm, embeddings, vector_store, memory_store)

    result = await engine.process(Interaction(content="hi there!"))

    assert result.decision is MemoryDecision.DISCARD
    assert result.memory is None
    assert len(memory_store.memories) == 0
    # Pipeline halted after policy evaluation.
    assert [s.step for s in result.trace.steps] == ["policy_evaluation"]


async def test_merge_path(llm, embeddings, vector_store, memory_store):
    existing = Memory(id="m1", content="User likes dark mode")
    await memory_store.save(existing)
    await vector_store.upsert("m1", await embeddings.embed("User likes dark mode"), {})

    llm.set("Evaluate whether", {"decision": "store", "reason": "pref", "matched_policy": "prefs"})
    llm.set("Extract a structured", {"type": "preference", "content": "User likes dark mode", "summary": "dark", "confidence": 0.9})
    llm.set("Determine whether", {"action": "merge", "target_memory_id": "m1", "reason": "same fact"})
    llm.set("Reconcile conflicting", {"action": "update", "reason": "no change", "updated_content": "User likes dark mode", "updated_summary": "dark"})

    engine = make_engine(llm, embeddings, vector_store, memory_store)
    result = await engine.process(Interaction(content="I really like dark mode"))

    assert result.decision is MemoryDecision.UPDATE
    assert result.merged_with == "m1"
    assert len(memory_store.memories) == 1


async def test_conflict_update_path(llm, embeddings, vector_store, memory_store):
    existing = Memory(id="m1", content="User prefers Python", version=1)
    await memory_store.save(existing)
    await vector_store.upsert("m1", await embeddings.embed("User prefers Python"), {})

    llm.set("Evaluate whether", {"decision": "store", "reason": "language pref", "matched_policy": "prefs"})
    llm.set("Extract a structured", {"type": "preference", "content": "User now develops in Rust", "summary": "Rust", "confidence": 0.95})
    llm.set("Determine whether", {"action": "merge", "target_memory_id": "m1", "reason": "same topic"})
    llm.set("Reconcile conflicting", {"action": "version", "reason": "switched to Rust", "updated_content": "User develops exclusively in Rust", "updated_summary": "Rust"})

    engine = make_engine(llm, embeddings, vector_store, memory_store)
    result = await engine.process(Interaction(content="I now develop exclusively in Rust"))

    assert result.decision is MemoryDecision.VERSION
    stored = memory_store.memories["m1"]
    assert stored.version == 2
    assert stored.content == "User develops exclusively in Rust"
    assert len(stored.metadata["version_history"]) == 1
    assert stored.metadata["version_history"][0]["content"] == "User prefers Python"


async def test_explainability_complete(llm, embeddings, vector_store, memory_store):
    llm.set("Evaluate whether", {"decision": "store", "reason": "pref", "matched_policy": "prefs"})
    llm.set("Extract a structured", {"type": "preference", "content": "X", "summary": "x", "confidence": 0.8})
    engine = make_engine(llm, embeddings, vector_store, memory_store)
    result = await engine.process(Interaction(content="something"))

    steps = [s.step for s in result.trace.steps]
    assert "policy_evaluation" in steps
    assert "memory_extraction" in steps
    assert "persistence" in steps
    assert "Decision:" in result.explanation


async def test_hook_injection(llm, embeddings, vector_store, memory_store):
    calls: list[str] = []

    class Auditor(BaseStage):
        name = "auditor"

        async def run(self, ctx: PipelineContext) -> PipelineContext:
            calls.append("post_persist")
            return ctx

    llm.set("Evaluate whether", {"decision": "store", "reason": "pref", "matched_policy": "prefs"})
    llm.set("Extract a structured", {"type": "fact", "content": "X", "summary": "x", "confidence": 0.8})
    engine = make_engine(
        llm, embeddings, vector_store, memory_store,
        hooks={HookPoint.POST_PERSIST: [Auditor()]},
    )
    await engine.process(Interaction(content="remember X"))
    assert calls == ["post_persist"]


async def test_retrieval(llm, embeddings, vector_store, memory_store):
    m = Memory(id="m1", content="User prefers dark mode", confidence=0.9)
    await memory_store.save(m)
    await vector_store.upsert("m1", await embeddings.embed("User prefers dark mode"), {})
    engine = make_engine(llm, embeddings, vector_store, memory_store)

    result = await engine.retrieve(RetrievalQuery(content="what theme?", min_confidence=0.5))
    assert len(result.memories) == 1
    assert result.memories[0].id == "m1"


async def test_retrieval_with_rerank(llm, embeddings, vector_store, memory_store):
    policy = PolicyConfig.default()
    policy.retrieval = RulesSection(rules="return relevant only")
    for i in range(2):
        m = Memory(id=f"m{i}", content=f"fact {i}", confidence=0.9)
        await memory_store.save(m)
        await vector_store.upsert(m.id, await embeddings.embed(m.content), {})
    llm.set("Rank and filter", {"memory_ids": ["m1"], "reason": "m1 most relevant"})

    engine = make_engine(llm, embeddings, vector_store, memory_store, policy=policy)
    result = await engine.retrieve(RetrievalQuery(content="query", min_confidence=0.5))
    assert [m.id for m in result.memories] == ["m1"]


async def test_context_builder_and_session(llm, embeddings, vector_store, memory_store):
    m = Memory(id="m1", content="User prefers dark mode", confidence=0.9)
    await memory_store.save(m)
    await vector_store.upsert("m1", await embeddings.embed("User prefers dark mode"), {})

    llm.set("Evaluate whether", {"decision": "discard", "reason": "q", "matched_policy": "x"})
    engine = make_engine(llm, embeddings, vector_store, memory_store)
    builder = ContextBuilder(engine.retriever, format=ContextFormat.MARKDOWN, min_confidence=0.5)
    session = MemorySession(engine, builder)

    ctx = await session.build_context("what theme do I like?")
    assert "User prefers dark mode" in ctx.formatted
    assert ctx.formatted.startswith("## Relevant memories")

    result = await session.ingest_turn("just chatting", "hello")
    assert result.decision is MemoryDecision.DISCARD


async def test_session_ingest_turn_splits_user_and_assistant(
    llm, embeddings, vector_store, memory_store
):
    llm.set("Evaluate whether", {"decision": "discard", "reason": "q", "matched_policy": "x"})
    engine = make_engine(llm, embeddings, vector_store, memory_store)
    session = MemorySession(engine, ContextBuilder(engine.retriever))

    await session.ingest_turn("I like chicken rice", "Here is a recipe for Hainanese chicken rice.")

    assert llm.calls
    policy_prompt = llm.calls[0]
    assert "User (evaluate for long-term memory)" in policy_prompt
    assert "I like chicken rice" in policy_prompt
    assert "Assistant (context only" in policy_prompt


async def test_context_builder_xml(llm, embeddings, vector_store, memory_store):
    m = Memory(id="m1", content="fact", confidence=0.9)
    await memory_store.save(m)
    await vector_store.upsert("m1", await embeddings.embed("fact"), {})
    engine = make_engine(llm, embeddings, vector_store, memory_store)
    builder = ContextBuilder(engine.retriever, format=ContextFormat.XML, min_confidence=0.5)
    ctx = await builder.build("q")
    assert "<memories>" in ctx.formatted
    assert "<memory>fact</memory>" in ctx.formatted
