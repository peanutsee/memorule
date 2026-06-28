# Setup guide

This guide walks you from a fresh Python project to a working memorule memory layer
with your own LLM, embedding model, and storage backends.

## Prerequisites

- Python 3.12+
- An LLM API (OpenAI, Anthropic, local model, etc.)
- An embedding API or local embedding model
- A vector store (Pinecone, Qdrant, etc.) and a document store for full `Memory` objects

memorule does **not** bundle provider SDKs. You add only the dependencies your backends need.

## 1. Install memorule

### With uv (recommended)

```bash
uv init my-agent
cd my-agent
uv add memorule
```

### With pip

```bash
pip install memorule
```

## 2. Scaffold project files

Run the CLI from your project root:

```bash
memorule init
```

This creates a `memorule/` directory:

```
memorule/
  memorule.yaml              # engine config
  policy/policy.yaml         # natural-language memory rules
  providers/
    llm.py.example
    embeddings.py.example
    stores.py.example
  hooks/
    example_auditor.py
```

Rename the `.example` provider stubs to `.py` and implement them (see step 4).

### Customize policy (optional)

Use the interactive wizard to refine rules:

```bash
memorule policy wizard
memorule policy wizard --section deduplication
```

Or edit `memorule/policy/policy.yaml` directly. The scaffold includes `memory_policy`,
`extraction`, `deduplication`, and `reconciliation` sections tuned for a generic agent
memory workflow (long-term user context, not session history).

```bash
memorule policy wizard --section extraction
```

### Minimum policy checklist

For most agents, tuning these three sections is enough before going live:

1. **`memory_policy.create_when`** — what lasting user context to store (preferences, projects, constraints)
2. **`memory_policy.discard_when`** — what to ignore (greetings, one-off questions, filler)
3. **`extraction.rules`** — preserve specifics in `content` / `summary`; `type` is optional

Add domain-specific detail only when your agent needs it (e.g. food, travel, support tickets).

## 3. Configure memorule.yaml

The scaffolded `memorule/memorule.yaml` controls retrieval defaults, context formatting, and LLM prompts:

```yaml
policy_path: policy/policy.yaml

retrieval:
  limit: 10
  min_confidence: 0.5

context:
  format: markdown          # markdown | xml | plain
  max_memories: 8
  header: "## Relevant memories"
  include_metadata: false

prompts:
  system: |
    You are a memory orchestration assistant for long-term agent memory.
    Preserve every specific entity the user stated; do not generalize.

  stages:
    policy_evaluation: |
      Decide whether this interaction should become a long-term memory.
    memory_extraction: |
      Extract a faithful memory from user statements.
    # ... deduplication, conflict_resolution, retrieval_rerank, etc.

  structured_output: auto   # auto | always | never

providers:
  llm: providers.llm:MyLanguageModel
  embeddings: providers.embeddings:MyEmbeddingModel
  vector_store: providers.stores:MyVectorStore
  memory_store: providers.stores:MyMemoryStore
```

**Prompts vs policy:** `policy.yaml` defines *what* to remember (create/discard rules, extraction fidelity).
`memorule.yaml` `prompts` defines *how* the LLM is instructed (system persona and per-stage guidance).
Pydantic response models define the output shape; JSON format hints are added automatically on the
fallback path when your provider does not support native structured output.

**Important:** `providers` paths are a **documented convention** for `memorule validate --check-providers`.
memorule does not auto-import them. You construct provider instances in your application code and
pass them to `MemoryEngine`.

Paths in `policy_path` are resolved relative to the directory containing `memorule.yaml`.

## 4. Implement providers

memorule depends on four small `Protocol` interfaces. No base class is required — duck typing is enough.

### LanguageModel

Used by policy-driven pipeline stages. At minimum, implement `complete()` returning raw text.
Optionally implement `complete_structured()` for native schema-enforced output when
`prompts.structured_output` is `auto` or `always`.

```python
# memorule/providers/llm.py
from pydantic import BaseModel

class MyLanguageModel:
    async def complete(self, prompt: str, *, system: str | None = None) -> str:
        # Call your LLM and return the response text.
        ...

    async def complete_structured[T: BaseModel](
        self,
        prompt: str,
        *,
        system: str | None = None,
        response_model: type[T],
    ) -> T:
        # Optional: OpenAI responses.parse, Anthropic structured outputs, etc.
        # If unsupported, memorule falls back to complete() + JSON parse when mode is auto.
        ...
```

With `structured_output: auto` (the default), text-only providers still work: memorule appends a
JSON schema hint derived from each stage's Pydantic model and parses the response. Set
`structured_output: never` to force that path for debugging.

### EmbeddingModel

Turns text into vectors for similarity search.

```python
# memorule/providers/embeddings.py
class MyEmbeddingModel:
    async def embed(self, text: str) -> list[float]:
        ...

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [await self.embed(t) for t in texts]
```

Use the **same embedding model** for writes and reads, or retrieval quality will suffer.
Vector dimension must match your vector store collection/index.

### VectorStore

Similarity index. Stores embeddings + lightweight metadata (`type`, `confidence`, `summary`).

```python
# memorule/providers/stores.py
class MyVectorStore:
    async def upsert(self, memory_id: str, embedding: list[float], metadata: dict) -> None:
        ...

    async def search(self, embedding: list[float], *, limit: int = 10) -> list[tuple[str, float]]:
        ...

    async def delete(self, memory_id: str) -> None:
        ...
```

For sync SDKs (Chroma, sqlite3, etc.), wrap calls with `asyncio.to_thread()` and keep a
**single long-lived client** on the instance. Do not call `.start()` on a reused `threading.Thread`
per operation — that causes `threads can only be started once` at persistence time.

### MemoryStore

Full `Memory` documents (content, version history, metadata).

```python
class MyMemoryStore:
    async def get(self, memory_id: str) -> Memory | None:
        ...

    async def save(self, memory: Memory) -> None:
        ...

    async def update(self, memory: Memory) -> None:
        ...

    async def delete(self, memory_id: str) -> None:
        ...

    async def list_by_ids(self, memory_ids: list[str]) -> list[Memory]:
        ...
```

Do not skip `MemoryStore` — even if your vector DB could hold payloads, memorule expects rich
`Memory` objects here for deduplication, reconciliation, and context building.

### Example dependencies

Add only what you need:

```bash
uv add openai pinecone-client   # example: OpenAI embeddings + Pinecone vectors
# or
uv add qdrant-client            # example: Qdrant vectors
```

See the [main README](../README.md#embeddings-and-vector-stores) for OpenAI, Qdrant, and Pinecone examples.

## 5. Validate configuration

Before wiring the engine, confirm config and policy parse correctly:

```bash
memorule validate memorule/memorule.yaml
```

After implementing providers and ensuring they are importable from your project root:

```bash
memorule validate memorule/memorule.yaml --check-providers
```

## 6. Wire MemoryEngine

Create the engine in your application entrypoint:

```python
import asyncio
from pathlib import Path

from memorule import MemoryEngine, load_config, load_policy

from providers.llm import MyLanguageModel
from providers.embeddings import MyEmbeddingModel
from providers.stores import MyVectorStore, MyMemoryStore

CONFIG_DIR = Path("memorule")

async def main() -> None:
    config = load_config(CONFIG_DIR / "memorule.yaml")
    policy = load_policy(config.resolve_policy_path(CONFIG_DIR))

    engine = MemoryEngine(
        llm=MyLanguageModel(),
        embeddings=MyEmbeddingModel(),
        vector_store=MyVectorStore(),
        memory_store=MyMemoryStore(),
        policy=policy,
        retrieval_limit=config.retrieval.limit,
    )

    # See docs/usage.md for the agent loop
    ...

if __name__ == "__main__":
    asyncio.run(main())
```

## 7. Environment variables

memorule has no built-in secrets management. Store API keys in environment variables and read
them inside your provider classes:

```python
import os

class MyLanguageModel:
    def __init__(self) -> None:
        self.api_key = os.environ["OPENAI_API_KEY"]
```

Typical variables for common backends:

| Backend | Example variables |
|---------|-------------------|
| OpenAI | `OPENAI_API_KEY` |
| Pinecone | `PINECONE_API_KEY`, index name in code or config |
| Qdrant | `QDRANT_URL`, optional `QDRANT_API_KEY` |

## Checklist

- [ ] `memorule` installed
- [ ] `memorule init` run; policy customized
- [ ] All four providers implemented
- [ ] `memorule validate` passes
- [ ] `MemoryEngine` constructed with matching embedding dimensions
- [ ] Agent loop uses read path before LLM and write path after (see [Usage](usage.md))

## Next steps

- [Usage guide](usage.md) — integrate retrieval and ingestion into your agent
- [Main README](../README.md#policy-example) — policy section reference
