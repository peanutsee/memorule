"""Similarity search stage: find nearby memories."""

from __future__ import annotations

from memorule.pipeline.context import PipelineContext
from memorule.pipeline.stage import BaseStage
from memorule.types import SimilarMemory


class SimilaritySearchStage(BaseStage):
    name = "similarity_search"

    def __init__(self, limit: int = 10):
        self.limit = limit

    async def run(self, ctx: PipelineContext) -> PipelineContext:
        if ctx.embedding is None:
            ctx.trace.add(self.name, decision="skipped", reason="No embedding available")
            return ctx

        hits = await ctx.vector_store.search(ctx.embedding, limit=self.limit)
        if not hits:
            ctx.trace.add(self.name, decision="no_matches", reason="No similar memories found")
            return ctx

        ids = [memory_id for memory_id, _ in hits]
        scores = {memory_id: score for memory_id, score in hits}
        memories = await ctx.memory_store.list_by_ids(ids)

        ctx.candidates = [
            SimilarMemory(memory=m, similarity=scores.get(m.id, 0.0)) for m in memories
        ]
        ctx.trace.add(
            self.name,
            decision="found",
            reason=f"Found {len(ctx.candidates)} candidate memories",
            candidate_ids=[c.memory.id for c in ctx.candidates],
        )
        return ctx
