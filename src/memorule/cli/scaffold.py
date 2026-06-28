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

prompts:
  system: |
    You are a memory orchestration assistant for long-term agent memory.
    Preserve every specific entity the user stated; do not generalize or replace
    concrete details with broad categories.

  stages:
    policy_evaluation: |
      Decide whether this interaction should become a long-term memory.
    memory_extraction: |
      Extract a faithful memory from user statements.
    metadata_enrichment: |
      Enrich the memory with retrieval-friendly metadata.
    deduplication: |
      Decide whether this memory duplicates an existing one.
    conflict_resolution: |
      Reconcile overlapping or conflicting memories.
    retrieval_rerank: |
      Rank memories by relevance to the query.

  structured_output: auto   # auto | always | never

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
    Store memories when the user reveals information that should persist across
    future conversations: preferences, constraints, ongoing projects or tasks,
    decisions, commitments, stable facts about themselves or their environment,
    and relationships to people, tools, or systems. Store brief follow-ups that
    refine earlier statements (e.g. "Actually use PostgreSQL instead").

  discard_when: |
    Ignore pure greetings or thanks with no new facts, one-off questions with no
    lasting user information, jokes, and filler small talk. Do not discard turns
    where the user adds or corrects long-term context.

extraction:
  rules: |
    Preserve every specific entity the user stated: names, dates, numbers, tools,
    projects, and constraints. Never replace specifics with generic categories
    (e.g. do not write "tech preference" when the user said "Rust").
    The summary must name the concrete subject (e.g. "Rust backend for API project"),
    not a broad category.
    The type field is optional; use a short free-form label only when helpful, otherwise omit.

deduplication:
  rules: |
    If two memories describe the same long-term fact or the same topic, merge or enrich them.
    Memories about the same subject should be enriched into one memory.
    If the new interaction adds additional details, enrich the existing memory.
    Preserve useful metadata. Avoid duplicate entries.

reconciliation:
  rules: |
    If new information contradicts an existing memory, prefer newer information.
    When enriching, merged content and summary must retain all specifics from both sides.
    Preserve previous values in version history. Record when the change occurred.

# Optional. Remove if you do not want metadata enrichment.
metadata_enrichment:
  rules: |
    Tag memories with specific entities (people, projects, tools, and topics) and relevant keywords
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
Memorule requires `complete`; optionally implement `complete_structured`
for native schema-enforced output when structured_output is auto or always.
"""

from __future__ import annotations

import json

from pydantic import BaseModel


class MyLanguageModel:
    async def complete(self, prompt: str, *, system: str | None = None) -> str:
        # Call your LLM provider here and return the raw text response.
        raise NotImplementedError("Implement MyLanguageModel.complete")

    async def complete_structured[T: BaseModel](
        self,
        prompt: str,
        *,
        system: str | None = None,
        response_model: type[T],
    ) -> T:
        # Optional: use your provider's native structured output API.
        # OpenAI: client.responses.parse(..., text_format=response_model)
        # Anthropic: tool_use / structured outputs
        # Fallback: schema in prompt + complete + model_validate
        schema = json.dumps(response_model.model_json_schema(), indent=2)
        raw = await self.complete(
            f"{prompt}\\n\\nRespond with JSON matching:\\n{schema}",
            system=system,
        )
        return response_model.model_validate(json.loads(raw))
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
