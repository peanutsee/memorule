"""Policy evaluation stage: store or discard."""

from __future__ import annotations

from memorule.pipeline.context import PipelineContext
from memorule.pipeline.stage import BaseStage
from memorule.prompts.parsing import parse_llm_response
from memorule.prompts.templates import (
    SYSTEM_PROMPT,
    PolicyEvaluationResponse,
    build_policy_evaluation_prompt,
)
from memorule.types import MemoryDecision


class PolicyEvaluationStage(BaseStage):
    name = "policy_evaluation"

    async def run(self, ctx: PipelineContext) -> PipelineContext:
        prompt = build_policy_evaluation_prompt(ctx.interaction, ctx.policy)
        raw = await ctx.llm.complete(prompt, system=SYSTEM_PROMPT)
        response = parse_llm_response(raw, PolicyEvaluationResponse, stage=self.name)

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
