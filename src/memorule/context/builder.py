"""ContextBuilder: format retrieved memories for LLM injection."""

from __future__ import annotations

from memorule.retrieval.retriever import MemoryRetriever
from memorule.types import (
    ContextFormat,
    Memory,
    MemoryContext,
    RetrievalQuery,
)


class ContextBuilder:
    def __init__(
        self,
        retriever: MemoryRetriever,
        *,
        format: ContextFormat = ContextFormat.MARKDOWN,
        max_memories: int = 8,
        header: str = "## Relevant memories",
        include_metadata: bool = False,
        min_confidence: float = 0.0,
    ):
        self.retriever = retriever
        self.format = ContextFormat(format)
        self.max_memories = max_memories
        self.header = header
        self.include_metadata = include_metadata
        self.min_confidence = min_confidence

    async def build(self, query: str) -> MemoryContext:
        result = await self.retriever.retrieve(
            RetrievalQuery(
                content=query,
                limit=self.max_memories,
                min_confidence=self.min_confidence,
            )
        )
        memories = result.memories[: self.max_memories]
        formatted = self._format(memories)
        return MemoryContext(memories=memories, formatted=formatted, trace=result.trace)

    def _format(self, memories: list[Memory]) -> str:
        if not memories:
            return ""
        if self.format is ContextFormat.MARKDOWN:
            return self._format_markdown(memories)
        if self.format is ContextFormat.XML:
            return self._format_xml(memories)
        return self._format_plain(memories)

    def _metadata_suffix(self, memory: Memory) -> str:
        if not self.include_metadata:
            return ""
        if memory.type is not None:
            return f" ({memory.type}, confidence: {memory.confidence})"
        return f" (confidence: {memory.confidence})"

    def _metadata_attrs(self, memory: Memory) -> str:
        if not self.include_metadata:
            return ""
        if memory.type is not None:
            return f' type="{memory.type}" confidence="{memory.confidence}"'
        return f' confidence="{memory.confidence}"'

    def _format_markdown(self, memories: list[Memory]) -> str:
        lines = [self.header, ""]
        for m in memories:
            lines.append(f"- {m.content}{self._metadata_suffix(m)}")
        return "\n".join(lines)

    def _format_xml(self, memories: list[Memory]) -> str:
        lines = ["<memories>"]
        for m in memories:
            lines.append(f"  <memory{self._metadata_attrs(m)}>{m.content}</memory>")
        lines.append("</memories>")
        return "\n".join(lines)

    def _format_plain(self, memories: list[Memory]) -> str:
        return "\n".join(m.content for m in memories)
