"""Policy evaluation stage: store or discard."""

from __future__ import annotations

from memorule.llm.invoke import invoke_structured
from memorule.pipeline.context import PipelineContext
from memorule.pipeline.stage import BaseStage
from memorule.prompts.templates import (
    PolicyEvaluationResponse,
    build_policy_evaluation_prompt,
)
from memorule.types import MemoryDecision


class PolicyEvaluationStage(BaseStage):
    name = "policy_evaluation"

    async def run(self, ctx: PipelineContext) -> PipelineContext:
        prompt = build_policy_evaluation_prompt(ctx.interaction, ctx.policy)
        system = ctx.prompts.resolve_system_prompt(self.name)
        response = await invoke_structured(
            ctx.llm,
            prompt,
            response_model=PolicyEvaluationResponse,
            system=system,
            stage=self.name,
            mode=ctx.prompts.structured_output,
        )

        ctx.reason = response.reason
        ctx.matched_policy = response.matched_policy

        if response.decision == "discard":
            ctx.decision = MemoryDecision.DISCARD
            ctx.halt = True
            ctx.trace.add(
                self.name,
                decision="discard",
                reason=response.reason,
                matched_policy=response.matched_policy,
            )
        else:
            ctx.decision = MemoryDecision.STORE
            ctx.trace.add(
                self.name,
                decision="store",
                reason=response.reason,
                matched_policy=response.matched_policy,
            )
        return ctx
