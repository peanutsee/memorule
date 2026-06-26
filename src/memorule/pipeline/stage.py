"""PipelineStage protocol and base helpers."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from memorule.pipeline.context import PipelineContext


@runtime_checkable
class PipelineStage(Protocol):
    name: str

    async def run(self, ctx: PipelineContext) -> PipelineContext: ...


class BaseStage:
    name: str = "base"

    async def run(self, ctx: PipelineContext) -> PipelineContext:  # pragma: no cover
        raise NotImplementedError
