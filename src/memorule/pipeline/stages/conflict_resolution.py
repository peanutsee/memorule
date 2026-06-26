"""Conflict resolution stage: reconcile evolving memories."""

from __future__ import annotations

from memorule.pipeline.context import PipelineContext
from memorule.pipeline.stage import BaseStage
from memorule.prompts.parsing import parse_llm_response
from memorule.prompts.templates import (
    SYSTEM_PROMPT,
    ReconciliationResponse,
    build_reconciliation_prompt,
)
from memorule.types import MemoryDecision, MemoryVersion, _utcnow


class ConflictResolutionStage(BaseStage):
    name = "conflict_resolution"

    async def run(self, ctx: PipelineContext) -> PipelineContext:
        if (
            ctx.memory is None
            or ctx.target_memory_id is None
            or ctx.decision not in (MemoryDecision.MERGE, MemoryDecision.UPDATE)
        ):
            ctx.trace.add(self.name, decision="skipped", reason="No conflicting memory to reconcile")
            return ctx

        existing = await ctx.memory_store.get(ctx.target_memory_id)
        if existing is None:
            ctx.target_memory_id = None
            ctx.decision = MemoryDecision.STORE
            ctx.trace.add(
                self.name,
                decision="new",
                reason="Target memory no longer exists; storing as new",
            )
            return ctx

        rules = ctx.policy.reconciliation.rules
        prompt = build_reconciliation_prompt(ctx.memory, existing, rules)
        raw = await ctx.llm.complete(prompt, system=SYSTEM_PROMPT)
        response = parse_llm_response(raw, ReconciliationResponse, stage=self.name)

        if response.action == "keep_existing":
            ctx.memory = existing
            ctx.decision = MemoryDecision.MERGE
            ctx.trace.add(self.name, decision="keep_existing", reason=response.reason)
            return ctx

        version_snapshot = MemoryVersion(
            content=existing.content,
            summary=existing.summary,
            version=existing.version,
            reason=response.reason,
        )
        history = existing.metadata.get("version_history", [])
        history.append(version_snapshot.model_dump(mode="json"))

        updated = existing.model_copy(deep=True)
        updated.content = response.updated_content or ctx.memory.content
        updated.summary = response.updated_summary or ctx.memory.summary
        updated.confidence = ctx.memory.confidence
        updated.updated_at = _utcnow()
        updated.metadata["version_history"] = history

        if response.action == "version":
            updated.version = existing.version + 1
            ctx.decision = MemoryDecision.VERSION
        else:
            ctx.decision = MemoryDecision.UPDATE

        ctx.memory = updated
        ctx.trace.add(
            self.name,
            decision=response.action,
            reason=response.reason,
            target_memory_id=existing.id,
            new_version=updated.version,
        )
        return ctx
