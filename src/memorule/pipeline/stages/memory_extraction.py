"""Memory extraction stage: produce structured Memory."""

from __future__ import annotations

from memorule.llm.invoke import invoke_structured
from memorule.pipeline.context import PipelineContext
from memorule.pipeline.stage import BaseStage
from memorule.prompts.templates import (
    ExtractionResponse,
    build_extraction_prompt,
)
from memorule.types import Memory, SimilarMemory

_PRE_EXTRACTION_LIMIT = 3


class MemoryExtractionStage(BaseStage):
    name = "memory_extraction"

    async def _pre_extraction_candidates(self, ctx: PipelineContext) -> list[SimilarMemory]:
        text = ctx.interaction.user_content or ctx.interaction.content
        embedding = await ctx.embeddings.embed(text)
        hits = await ctx.vector_store.search(embedding, limit=_PRE_EXTRACTION_LIMIT)
        if not hits:
            return []

        scores = {memory_id: score for memory_id, score in hits}
        ids = [memory_id for memory_id, _ in hits]
        memories = await ctx.memory_store.list_by_ids(ids)
        return [
            SimilarMemory(memory=m, similarity=scores.get(m.id, 0.0)) for m in memories
        ]

    async def run(self, ctx: PipelineContext) -> PipelineContext:
        candidates = await self._pre_extraction_candidates(ctx)
        prompt = build_extraction_prompt(ctx.interaction, ctx.policy, candidates)
        system = ctx.prompts.resolve_system_prompt(self.name)
        response = await invoke_structured(
            ctx.llm,
            prompt,
            response_model=ExtractionResponse,
            system=system,
            stage=self.name,
            mode=ctx.prompts.structured_output,
        )

        ctx.memory = Memory(
            type=response.type,
            content=response.content,
            summary=response.summary,
            confidence=response.confidence,
            source=ctx.interaction.source,
            metadata=dict(ctx.interaction.metadata),
        )
        ctx.trace.add(
            self.name,
            decision="extracted",
            reason=(
                f"Extracted {response.type} memory"
                if response.type
                else "Extracted memory"
            ),
            content=response.content,
            confidence=response.confidence,
            pre_extraction_candidates=[c.memory.id for c in candidates],
        )
        return ctx
