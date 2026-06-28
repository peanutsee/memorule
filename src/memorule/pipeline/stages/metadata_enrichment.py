"""Metadata enrichment stage: add categorization/tags."""

from __future__ import annotations

from memorule.llm.invoke import invoke_structured
from memorule.pipeline.context import PipelineContext
from memorule.pipeline.stage import BaseStage
from memorule.prompts.templates import (
    MetadataEnrichmentResponse,
    build_metadata_enrichment_prompt,
)


class MetadataEnrichmentStage(BaseStage):
    name = "metadata_enrichment"

    async def run(self, ctx: PipelineContext) -> PipelineContext:
        if ctx.policy.metadata_enrichment is None or ctx.memory is None:
            ctx.trace.add(self.name, decision="skipped", reason="No enrichment rules configured")
            return ctx

        rules = ctx.policy.metadata_enrichment.rules
        prompt = build_metadata_enrichment_prompt(ctx.memory, rules)
        system = ctx.prompts.resolve_system_prompt(self.name)
        response = await invoke_structured(
            ctx.llm,
            prompt,
            response_model=MetadataEnrichmentResponse,
            system=system,
            stage=self.name,
            mode=ctx.prompts.structured_output,
        )

        if response.tags:
            ctx.memory.metadata["tags"] = response.tags
        if response.category:
            ctx.memory.metadata["category"] = response.category
        ctx.memory.metadata.update(response.metadata)

        ctx.trace.add(
            self.name,
            decision="enriched",
            reason=response.reason,
            tags=response.tags,
            category=response.category,
        )
        return ctx
