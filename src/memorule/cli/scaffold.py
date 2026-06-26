"""Scaffold file templates for `memorule init` and `hooks new`."""

from __future__ import annotations

MEMORULE_YAML = """\
# Memorule engine configuration.
# Policy rules (natural language) live separately in policy/policy.yaml.

policy_path: policy/policy.yaml

retrieval:
  limit: 10
  min_confidence: 0.5

context:
  format: markdown          # markdown | xml | plain
  max_memories: 8
  header: "## Relevant memories"
  include_metadata: false   # include type/confidence in formatted output

# Provider paths are a documented convention only. Memorule does not
# auto-load these; wire your implementations in your application code.
providers:
  llm: providers.llm:MyLanguageModel
  embeddings: providers.embeddings:MyEmbeddingModel
  vector_store: providers.stores:MyVectorStore
  memory_store: providers.stores:MyMemoryStore
"""

POLICY_YAML = """\
# Natural-language memory policy. These rules are interpreted by your LLM.

memory_policy:
  create_when: |
    Store memories when an interaction reveals
    long-term user preferences,
    ongoing projects,
    recurring facts,
    commitments,
    relationships,
    or information that will likely be useful in future conversations.

  discard_when: |
    Ignore greetings,
    temporary requests,
    jokes,
    casual conversation,
    and one-off questions.

deduplication:
  rules: |
    If two memories describe the same long-term fact, merge them.
    If the new interaction adds additional details, enrich the existing memory.
    Preserve useful metadata.
    Avoid duplicate entries.

reconciliation:
  rules: |
    If new information contradicts an existing memory, prefer newer information.
    Preserve previous values in version history.
    Record when the change occurred.

# Optional. Remove if you do not want metadata enrichment.
metadata_enrichment:
  rules: |
    Tag memories with a short category and relevant keywords
    that will make them easier to retrieve later.

# Optional. Enables LLM re-ranking during retrieval.
retrieval:
  rules: |
    Return only memories that are directly relevant to the user's query,
    ordered from most to least relevant.
"""

LLM_PROVIDER = '''\
"""Example LanguageModel implementation.

Rename this file to llm.py and implement against your provider.
Memorule only requires the `complete` coroutine.
"""

from __future__ import annotations


class MyLanguageModel:
    async def complete(self, prompt: str, *, system: str | None = None) -> str:
        # Call your LLM provider here and return the raw text response.
        # The framework expects JSON in the response for policy-driven stages.
        raise NotImplementedError("Implement MyLanguageModel.complete")
'''

EMBEDDINGS_PROVIDER = '''\
"""Example EmbeddingModel implementation.

Rename this file to embeddings.py and implement against your provider.
"""

from __future__ import annotations


class MyEmbeddingModel:
    async def embed(self, text: str) -> list[float]:
        raise NotImplementedError("Implement MyEmbeddingModel.embed")

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [await self.embed(t) for t in texts]
'''

STORES_PROVIDER = '''\
"""Example VectorStore and MemoryStore implementations.

Rename this file to stores.py and back them with your databases.
"""

from __future__ import annotations

from memorule import Memory


class MyVectorStore:
    async def upsert(
        self, memory_id: str, embedding: list[float], metadata: dict
    ) -> None:
        raise NotImplementedError

    async def search(
        self, embedding: list[float], *, limit: int = 10
    ) -> list[tuple[str, float]]:
        raise NotImplementedError

    async def delete(self, memory_id: str) -> None:
        raise NotImplementedError


class MyMemoryStore:
    async def get(self, memory_id: str) -> Memory | None:
        raise NotImplementedError

    async def save(self, memory: Memory) -> None:
        raise NotImplementedError

    async def update(self, memory: Memory) -> None:
        raise NotImplementedError

    async def delete(self, memory_id: str) -> None:
        raise NotImplementedError

    async def list_by_ids(self, memory_ids: list[str]) -> list[Memory]:
        raise NotImplementedError
'''

HOOKS_INIT = '"""Custom pipeline hooks."""\n'

EXAMPLE_HOOK = '''\
"""Example pipeline hook.

A hook is any object with a `name` attribute and an async `run(ctx)` method.
Register it at a HookPoint when constructing the MemoryEngine:

    from memorule import HookPoint, MemoryEngine
    from hooks.example_auditor import Auditor

    engine = MemoryEngine(..., hooks={HookPoint.POST_PERSIST: [Auditor()]})
"""

from __future__ import annotations

from memorule import BaseStage
from memorule.pipeline.context import PipelineContext


class Auditor(BaseStage):
    name = "auditor"

    async def run(self, ctx: PipelineContext) -> PipelineContext:
        # Observe without mutating. Logs the decision so far.
        if ctx.memory is not None:
            print(f"[auditor] decision={ctx.decision} memory_id={ctx.memory.id}")
        return ctx
'''


def hook_template(class_name: str) -> str:
    return f'''\
"""Custom pipeline hook: {class_name}."""

from __future__ import annotations

from memorule import BaseStage
from memorule.pipeline.context import PipelineContext


class {class_name}(BaseStage):
    name = "{class_name.lower()}"

    async def run(self, ctx: PipelineContext) -> PipelineContext:
        # Implement your hook logic here.
        return ctx
'''
