"""Embedding generation stage."""

from __future__ import annotations

from memorule.pipeline.context import PipelineContext
from memorule.pipeline.stage import BaseStage


class EmbeddingGenerationStage(BaseStage):
    name = "embedding_generation"

    async def run(self, ctx: PipelineContext) -> PipelineContext:
        if ctx.memory is None:
            ctx.trace.add(self.name, decision="skipped", reason="No memory to embed")
            return ctx

        ctx.embedding = await ctx.embeddings.embed(ctx.memory.content)
        ctx.trace.add(
            self.name,
            decision="embedded",
            reason="Generated embedding for memory content",
            dimensions=len(ctx.embedding),
        )
        return ctx
