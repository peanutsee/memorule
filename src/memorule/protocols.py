"""Protocol interfaces for user-supplied integrations."""

from __future__ import annotations

from typing import Any, Protocol, TypeVar, runtime_checkable

from pydantic import BaseModel

from memorule.types import Memory

T = TypeVar("T", bound=BaseModel)


@runtime_checkable
class LanguageModel(Protocol):
    async def complete(self, prompt: str, *, system: str | None = None) -> str: ...


@runtime_checkable
class StructuredLanguageModel(LanguageModel, Protocol):
    async def complete_structured(
        self,
        prompt: str,
        *,
        system: str | None = None,
        response_model: type[T],
    ) -> T: ...


@runtime_checkable
class EmbeddingModel(Protocol):
    async def embed(self, text: str) -> list[float]: ...

    async def embed_batch(self, texts: list[str]) -> list[list[float]]: ...


@runtime_checkable
class VectorStore(Protocol):
    async def upsert(
        self, memory_id: str, embedding: list[float], metadata: dict[str, Any]
    ) -> None: ...

    async def search(
        self, embedding: list[float], *, limit: int = 10
    ) -> list[tuple[str, float]]: ...

    async def delete(self, memory_id: str) -> None: ...


@runtime_checkable
class MemoryStore(Protocol):
    async def get(self, memory_id: str) -> Memory | None: ...

    async def save(self, memory: Memory) -> None: ...

    async def update(self, memory: Memory) -> None: ...

    async def delete(self, memory_id: str) -> None: ...

    async def list_by_ids(self, memory_ids: list[str]) -> list[Memory]: ...
