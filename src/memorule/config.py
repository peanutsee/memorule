"""Engine configuration loaded from memorule.yaml."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from memorule.exceptions import ConfigError
from memorule.types import ContextFormat


class StructuredOutputMode(StrEnum):
    AUTO = "auto"
    ALWAYS = "always"
    NEVER = "never"


_DEFAULT_SYSTEM = (
    "You are a memory orchestration assistant for long-term agent memory. "
    "Preserve every specific entity the user stated; do not generalize or replace "
    "concrete details with broad categories."
)

_DEFAULT_STAGE_PROMPTS: dict[str, str] = {
    "policy_evaluation": "Decide whether this interaction should become a long-term memory.",
    "memory_extraction": "Extract a faithful memory from user statements.",
    "metadata_enrichment": "Enrich the memory with retrieval-friendly metadata.",
    "deduplication": "Decide whether this memory duplicates an existing one.",
    "conflict_resolution": "Reconcile overlapping or conflicting memories.",
    "retrieval_rerank": "Rank memories by relevance to the query.",
}


class PromptConfig(BaseModel):
    system: str = _DEFAULT_SYSTEM
    stages: dict[str, str] = Field(default_factory=lambda: dict(_DEFAULT_STAGE_PROMPTS))
    structured_output: StructuredOutputMode = StructuredOutputMode.AUTO

    @classmethod
    def default(cls) -> PromptConfig:
        return cls()

    def resolve_system_prompt(self, stage: str) -> str:
        stage_prompt = self.stages.get(stage)
        if stage_prompt:
            return f"{self.system}\n\n{stage_prompt}".strip()
        return self.system


class RetrievalConfig(BaseModel):
    limit: int = 10
    min_confidence: float = 0.5


class ContextConfig(BaseModel):
    format: ContextFormat = ContextFormat.MARKDOWN
    max_memories: int = 8
    header: str = "## Relevant memories"
    include_metadata: bool = False


class ProvidersConfig(BaseModel):
    llm: str = "providers.llm:MyLanguageModel"
    embeddings: str = "providers.embeddings:MyEmbeddingModel"
    vector_store: str = "providers.stores:MyVectorStore"
    memory_store: str = "providers.stores:MyMemoryStore"


class MemoruleConfig(BaseModel):
    policy_path: str = "policy/policy.yaml"
    retrieval: RetrievalConfig = Field(default_factory=RetrievalConfig)
    context: ContextConfig = Field(default_factory=ContextConfig)
    prompts: PromptConfig = Field(default_factory=PromptConfig.default)
    providers: ProvidersConfig = Field(default_factory=ProvidersConfig)

    def resolve_policy_path(self, base_dir: Path | None = None) -> Path:
        path = Path(self.policy_path)
        if path.is_absolute():
            return path
        if base_dir is not None:
            return base_dir / path
        return path


def load_config(path: str | Path) -> MemoruleConfig:
    config_path = Path(path)
    if not config_path.exists():
        raise ConfigError(f"Config file not found: {config_path}")

    with config_path.open(encoding="utf-8") as f:
        raw: Any = yaml.safe_load(f)

    if not isinstance(raw, dict):
        raise ConfigError(f"Config file must contain a YAML mapping: {config_path}")

    try:
        return MemoruleConfig.model_validate(raw)
    except Exception as exc:
        raise ConfigError(f"Invalid memorule configuration in {config_path}: {exc}") from exc
