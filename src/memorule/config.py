"""Engine configuration loaded from memorule.yaml."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from memorule.exceptions import ConfigError
from memorule.types import ContextFormat


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
