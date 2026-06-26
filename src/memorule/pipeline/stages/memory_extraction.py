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
from memorule.types import Memory


class MemoryExtractionStage(BaseStage):
    name = "memory_extraction"

    async def run(self, ctx: PipelineContext) -> PipelineContext:
        prompt = build_extraction_prompt(ctx.interaction)
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
            reason=f"Extracted {response.type} memory",
            content=response.content,
            confidence=response.confidence,
        )
        return ctx
