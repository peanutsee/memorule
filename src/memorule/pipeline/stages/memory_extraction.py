"""Memory extraction stage: produce structured Memory."""

from __future__ import annotations

from memorule.pipeline.context import PipelineContext
from memorule.pipeline.stage import BaseStage
from memorule.prompts.parsing import parse_llm_response
from memorule.prompts.templates import (
    SYSTEM_PROMPT,
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
        raw = await ctx.llm.complete(prompt, system=SYSTEM_PROMPT)
        response = parse_llm_response(raw, ExtractionResponse, stage=self.name)

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
