"""Deduplication stage: decide new/merge/enrich."""

from __future__ import annotations

from memorule.pipeline.context import PipelineContext
from memorule.pipeline.stage import BaseStage
from memorule.prompts.parsing import parse_llm_response
from memorule.prompts.templates import (
    SYSTEM_PROMPT,
    DeduplicationResponse,
    build_deduplication_prompt,
)
from memorule.types import MemoryDecision


class DeduplicationStage(BaseStage):
    name = "deduplication"

    async def run(self, ctx: PipelineContext) -> PipelineContext:
        if ctx.memory is None or not ctx.candidates:
            ctx.trace.add(
                self.name,
                decision="new",
                reason="No candidates to compare; treating as new memory",
            )
            return ctx

        rules = ctx.policy.deduplication.rules
        prompt = build_deduplication_prompt(ctx.memory, ctx.candidates, rules)
        raw = await ctx.llm.complete(prompt, system=SYSTEM_PROMPT)
        response = parse_llm_response(raw, DeduplicationResponse, stage=self.name)

        if response.action == "new":
            ctx.trace.add(self.name, decision="new", reason=response.reason)
            return ctx

        ctx.target_memory_id = response.target_memory_id
        if response.action == "merge":
            ctx.decision = MemoryDecision.MERGE
        else:
            ctx.decision = MemoryDecision.UPDATE

        ctx.trace.add(
            self.name,
            decision=response.action,
            reason=response.reason,
            target_memory_id=response.target_memory_id,
        )
        return ctx
