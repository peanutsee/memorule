"""Deduplication stage: decide new/merge/enrich."""

from __future__ import annotations

from memorule.llm.invoke import invoke_structured
from memorule.pipeline.context import PipelineContext
from memorule.pipeline.stage import BaseStage
from memorule.prompts.templates import (
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
        system = ctx.prompts.resolve_system_prompt(self.name)
        response = await invoke_structured(
            ctx.llm,
            prompt,
            response_model=DeduplicationResponse,
            system=system,
            stage=self.name,
            mode=ctx.prompts.structured_output,
        )

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
