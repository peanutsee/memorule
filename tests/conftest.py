"""Shared test fakes (test-only, not shipped)."""

from __future__ import annotations

import hashlib
import json

import pytest

from memorule import Memory
from memorule.policy.config import PolicyConfig


class FakeLanguageModel:
    """Returns canned JSON responses keyed by substring match in the prompt."""

    def __init__(self, responses: dict[str, dict] | None = None):
        self.responses = responses or {}
        self.calls: list[str] = []

    def set(self, key: str, response: dict) -> None:
        self.responses[key] = response

    async def complete(self, prompt: str, *, system: str | None = None) -> str:
        self.calls.append(prompt)
        for key, response in self.responses.items():
            if key in prompt:
                return json.dumps(response)
        raise AssertionError(f"No canned response matched prompt:\n{prompt[:200]}")


class FakeEmbeddingModel:
    """Deterministic hash-based vectors."""

    def __init__(self, dim: int = 8):
        self.dim = dim

    def _vec(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode()).digest()
        return [digest[i % len(digest)] / 255.0 for i in range(self.dim)]

    async def embed(self, text: str) -> list[float]:
        return self._vec(text)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self._vec(t) for t in texts]


class FakeVectorStore:
    def __init__(self) -> None:
        self.vectors: dict[str, list[float]] = {}
        self.metadata: dict[str, dict] = {}
        self.forced_hits: list[tuple[str, float]] | None = None

    async def upsert(self, memory_id: str, embedding: list[float], metadata: dict) -> None:
        self.vectors[memory_id] = embedding
        self.metadata[memory_id] = metadata

    async def search(self, embedding: list[float], *, limit: int = 10) -> list[tuple[str, float]]:
        if self.forced_hits is not None:
            return self.forced_hits[:limit]

        def cosine(a: list[float], b: list[float]) -> float:
            num = sum(x * y for x, y in zip(a, b))
            da = sum(x * x for x in a) ** 0.5
            db = sum(y * y for y in b) ** 0.5
            return num / (da * db) if da and db else 0.0

        scored = [(mid, cosine(embedding, vec)) for mid, vec in self.vectors.items()]
        scored.sort(key=lambda t: t[1], reverse=True)
        return scored[:limit]

    async def delete(self, memory_id: str) -> None:
        self.vectors.pop(memory_id, None)
        self.metadata.pop(memory_id, None)


class FakeMemoryStore:
    def __init__(self) -> None:
        self.memories: dict[str, Memory] = {}

    async def get(self, memory_id: str) -> Memory | None:
        return self.memories.get(memory_id)

    async def save(self, memory: Memory) -> None:
        self.memories[memory.id] = memory

    async def update(self, memory: Memory) -> None:
        self.memories[memory.id] = memory

    async def delete(self, memory_id: str) -> None:
        self.memories.pop(memory_id, None)

    async def list_by_ids(self, memory_ids: list[str]) -> list[Memory]:
        return [self.memories[mid] for mid in memory_ids if mid in self.memories]


@pytest.fixture
def llm() -> FakeLanguageModel:
    return FakeLanguageModel()


@pytest.fixture
def embeddings() -> FakeEmbeddingModel:
    return FakeEmbeddingModel()


@pytest.fixture
def vector_store() -> FakeVectorStore:
    return FakeVectorStore()


@pytest.fixture
def memory_store() -> FakeMemoryStore:
    return FakeMemoryStore()


@pytest.fixture
def policy() -> PolicyConfig:
    return PolicyConfig.default()
