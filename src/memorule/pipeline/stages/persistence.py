"""Persistence stage: save to stores."""

from __future__ import annotations

from typing import Any

from memorule.pipeline.context import PipelineContext
from memorule.pipeline.stage import BaseStage
from memorule.types import MemoryDecision


class PersistenceStage(BaseStage):
    name = "persistence"

    async def run(self, ctx: PipelineContext) -> PipelineContext:
        if ctx.memory is None:
            ctx.trace.add(self.name, decision="skipped", reason="No memory to persist")
            return ctx

        is_update = ctx.decision in (
            MemoryDecision.MERGE,
            MemoryDecision.UPDATE,
            MemoryDecision.VERSION,
        )

        if is_update:
            await ctx.memory_store.update(ctx.memory)
        else:
            ctx.decision = ctx.decision or MemoryDecision.STORE
            await ctx.memory_store.save(ctx.memory)

        if ctx.embedding is not None:
            content_preview = (ctx.memory.content or "")[:200]
            metadata: dict[str, Any] = {
                "confidence": ctx.memory.confidence,
                "summary": ctx.memory.summary or "",
                "content": content_preview,
            }
            if ctx.memory.type is not None:
                metadata["type"] = ctx.memory.type
            await ctx.vector_store.upsert(
                ctx.memory.id,
                ctx.embedding,
                metadata,
            )

        ctx.trace.add(
            self.name,
            decision="persisted",
            reason="Updated existing memory" if is_update else "Saved new memory",
            memory_id=ctx.memory.id,
        )
        return ctx
