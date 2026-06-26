"""MemorySession: thin retrieve+ingest coordinator per turn."""

from __future__ import annotations

from typing import Any

from memorule.context.builder import ContextBuilder
from memorule.pipeline.engine import MemoryEngine
from memorule.types import Interaction, MemoryContext, PipelineResult


class MemorySession:
    """Bundles the read (retrieve) and write (ingest) touchpoints.

    Holds no conversation state; conversation/session history remains the
    responsibility of the calling agent.
    """

    def __init__(self, engine: MemoryEngine, context_builder: ContextBuilder):
        self.engine = engine
        self.context_builder = context_builder

    async def build_context(self, query: str) -> MemoryContext:
        return await self.context_builder.build(query)

    async def ingest_turn(
        self,
        user_message: str,
        assistant_message: str | None = None,
        *,
        source: str = "conversation",
        metadata: dict[str, Any] | None = None,
    ) -> PipelineResult:
        if assistant_message is not None:
            content = f"User: {user_message}\nAssistant: {assistant_message}"
        else:
            content = user_message
        interaction = Interaction(
            content=content,
            source=source,
            metadata=metadata or {},
        )
        return await self.engine.process(interaction)

    async def ingest(self, interaction: Interaction) -> PipelineResult:
        return await self.engine.process(interaction)
