"""MemoryRetriever: vector search with optional LLM re-ranking."""

from __future__ import annotations

from memorule.policy.config import PolicyConfig
from memorule.protocols import EmbeddingModel, LanguageModel, MemoryStore, VectorStore
from memorule.prompts.parsing import parse_llm_response
from memorule.prompts.templates import (
    SYSTEM_PROMPT,
    RetrievalRerankResponse,
    build_retrieval_rerank_prompt,
)
from memorule.types import ExplainabilityTrace, Memory, RetrievalQuery, RetrievalResult


class MemoryRetriever:
    def __init__(
        self,
        *,
        embeddings: EmbeddingModel,
        vector_store: VectorStore,
        memory_store: MemoryStore,
        llm: LanguageModel | None = None,
        policy: PolicyConfig | None = None,
    ):
        self.embeddings = embeddings
        self.vector_store = vector_store
        self.memory_store = memory_store
        self.llm = llm
        self.policy = policy

    async def retrieve(self, query: RetrievalQuery) -> RetrievalResult:
        trace = ExplainabilityTrace()
        embedding = await self.embeddings.embed(query.content)
        hits = await self.vector_store.search(embedding, limit=query.limit)

        if not hits:
            trace.add("vector_search", decision="no_matches", reason="No memories found")
            return RetrievalResult(memories=[], scores=[], trace=trace)

        scores = {memory_id: score for memory_id, score in hits}
        memories = await self.memory_store.list_by_ids([mid for mid, _ in hits])
        memories = [m for m in memories if m.confidence >= query.min_confidence]
        trace.add(
            "vector_search",
            decision="found",
            reason=f"Retrieved {len(memories)} memories",
            memory_ids=[m.id for m in memories],
        )

        rerank = self.policy is not None and self.policy.retrieval is not None and self.llm is not None
        if rerank and memories:
            memories = await self._rerank(query.content, memories, trace)

        ordered_scores = [scores.get(m.id, 0.0) for m in memories]
        return RetrievalResult(memories=memories, scores=ordered_scores, trace=trace)

    async def _rerank(
        self, query: str, memories: list[Memory], trace: ExplainabilityTrace
    ) -> list[Memory]:
        assert self.policy is not None and self.policy.retrieval is not None
        assert self.llm is not None
        prompt = build_retrieval_rerank_prompt(query, memories, self.policy.retrieval.rules)
        raw = await self.llm.complete(prompt, system=SYSTEM_PROMPT)
        response = parse_llm_response(raw, RetrievalRerankResponse, stage="retrieval_rerank")

        by_id = {m.id: m for m in memories}
        reranked = [by_id[mid] for mid in response.memory_ids if mid in by_id]
        trace.add(
            "rerank",
            decision="reranked",
            reason=response.reason,
            memory_ids=[m.id for m in reranked],
        )
        return reranked
