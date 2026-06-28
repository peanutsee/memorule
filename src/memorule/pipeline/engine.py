"""MemoryEngine: orchestrates the pipeline."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from memorule.config import PromptConfig
from memorule.exceptions import StageExecutionError
from memorule.pipeline.context import PipelineContext
from memorule.pipeline.stage import PipelineStage
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
from memorule.policy.config import PolicyConfig
from memorule.policy.loader import load_policy
from memorule.protocols import EmbeddingModel, LanguageModel, MemoryStore, VectorStore
from memorule.retrieval.retriever import MemoryRetriever
from memorule.types import (
    Interaction,
    MemoryDecision,
    PipelineResult,
    RetrievalQuery,
    RetrievalResult,
)


class HookPoint(StrEnum):
    PRE_POLICY = "pre_policy"
    POST_EXTRACTION = "post_extraction"
    POST_ENRICHMENT = "post_enrichment"
    PRE_PERSIST = "pre_persist"
    POST_PERSIST = "post_persist"


_DEFAULT_HOOK_ORDER = {
    HookPoint.PRE_POLICY: 0,
    HookPoint.POST_EXTRACTION: 2,
    HookPoint.POST_ENRICHMENT: 3,
    HookPoint.PRE_PERSIST: 7,
    HookPoint.POST_PERSIST: 8,
}


class MemoryEngine:
    def __init__(
        self,
        *,
        llm: LanguageModel,
        embeddings: EmbeddingModel,
        vector_store: VectorStore,
        memory_store: MemoryStore,
        policy: PolicyConfig | str | Path,
        prompts: PromptConfig | None = None,
        stages: list[PipelineStage] | None = None,
        hooks: dict[HookPoint, list[PipelineStage]] | None = None,
        retrieval_limit: int = 10,
    ):
        self.llm = llm
        self.embeddings = embeddings
        self.vector_store = vector_store
        self.memory_store = memory_store
        self.policy = policy if isinstance(policy, PolicyConfig) else load_policy(policy)
        self.prompts = prompts or PromptConfig.default()
        self.hooks = hooks or {}
        self._stages = stages or self._default_stages(retrieval_limit)
        self.retriever = MemoryRetriever(
            embeddings=embeddings,
            vector_store=vector_store,
            memory_store=memory_store,
            llm=llm,
            policy=self.policy,
            prompts=self.prompts,
        )

    @staticmethod
    def _default_stages(retrieval_limit: int) -> list[PipelineStage]:
        return [
            PolicyEvaluationStage(),
            MemoryExtractionStage(),
            MetadataEnrichmentStage(),
            EmbeddingGenerationStage(),
            SimilaritySearchStage(limit=retrieval_limit),
            DeduplicationStage(),
            ConflictResolutionStage(),
            PersistenceStage(),
        ]

    def _build_pipeline(self) -> list[PipelineStage]:
        if not self.hooks:
            return list(self._stages)

        pipeline: list[PipelineStage] = []
        hook_by_index: dict[int, list[PipelineStage]] = {}
        for point, stage_list in self.hooks.items():
            hook_by_index.setdefault(_DEFAULT_HOOK_ORDER[point], []).extend(stage_list)

        for index, stage in enumerate(self._stages):
            pipeline.extend(hook_by_index.get(index, []))
            pipeline.append(stage)
        pipeline.extend(hook_by_index.get(len(self._stages), []))
        return pipeline

    async def process(self, interaction: Interaction) -> PipelineResult:
        ctx = PipelineContext(
            interaction=interaction,
            policy=self.policy,
            prompts=self.prompts,
            llm=self.llm,
            embeddings=self.embeddings,
            vector_store=self.vector_store,
            memory_store=self.memory_store,
        )

        for stage in self._build_pipeline():
            if ctx.halt:
                break
            try:
                ctx = await stage.run(ctx)
            except StageExecutionError:
                raise
            except Exception as exc:
                raise StageExecutionError(
                    f"Stage '{getattr(stage, 'name', type(stage).__name__)}' failed: {exc}",
                    stage=getattr(stage, "name", type(stage).__name__),
                    cause=exc,
                ) from exc

        return PipelineResult(
            decision=ctx.decision or MemoryDecision.DISCARD,
            reason=ctx.reason,
            matched_policy=ctx.matched_policy,
            memory=ctx.memory if ctx.decision != MemoryDecision.DISCARD else None,
            merged_with=ctx.target_memory_id,
            confidence=ctx.memory.confidence if ctx.memory else None,
            trace=ctx.trace,
        )

    async def retrieve(self, query: RetrievalQuery) -> RetrievalResult:
        return await self.retriever.retrieve(query)
