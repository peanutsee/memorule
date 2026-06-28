"""MemoryRetriever: vector search with optional LLM re-ranking."""

from __future__ import annotations

from memorule.config import PromptConfig
from memorule.llm.invoke import invoke_structured
from memorule.policy.config import PolicyConfig
from memorule.protocols import EmbeddingModel, LanguageModel, MemoryStore, VectorStore
from memorule.prompts.templates import (
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
        prompts: PromptConfig | None = None,
    ):
        self.embeddings = embeddings
        self.vector_store = vector_store
        self.memory_store = memory_store
        self.llm = llm
        self.policy = policy
        self.prompts = prompts or PromptConfig.default()

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
        system = self.prompts.resolve_system_prompt("retrieval_rerank")
        response = await invoke_structured(
            self.llm,
            prompt,
            response_model=RetrievalRerankResponse,
            system=system,
            stage="retrieval_rerank",
            mode=self.prompts.structured_output,
        )

        by_id = {m.id: m for m in memories}
        reranked = [by_id[mid] for mid in response.memory_ids if mid in by_id]
        trace.add(
            "rerank",
            decision="reranked",
            reason=response.reason,
            memory_ids=[m.id for m in reranked],
        )
        return reranked
