"""Memorule: rule-first, model-agnostic long-term memory orchestration."""

from memorule.config import MemoruleConfig, load_config
from memorule.context import ContextBuilder, MemoryContext, MemorySession
from memorule.exceptions import (
    ConfigError,
    MemoruleError,
    MemoryNotFoundError,
    PolicyParseError,
    StageExecutionError,
)
from memorule.pipeline.engine import HookPoint, MemoryEngine
from memorule.pipeline.stage import BaseStage, PipelineStage
from memorule.policy import PolicyConfig, load_policy
from memorule.protocols import EmbeddingModel, LanguageModel, MemoryStore, VectorStore
from memorule.retrieval import MemoryRetriever
from memorule.types import (
    ContextFormat,
    ExplainabilityTrace,
    Interaction,
    Memory,
    MemoryDecision,
    MemoryVersion,
    PipelineResult,
    RetrievalQuery,
    RetrievalResult,
    SimilarMemory,
)

__version__ = "0.1.0"

__all__ = [
    "BaseStage",
    "ConfigError",
    "ContextBuilder",
    "ContextFormat",
    "EmbeddingModel",
    "ExplainabilityTrace",
    "HookPoint",
    "Interaction",
    "LanguageModel",
    "Memory",
    "MemoryContext",
    "MemoryDecision",
    "MemoryEngine",
    "MemoryNotFoundError",
    "MemoryRetriever",
    "MemorySession",
    "MemoryStore",
    "MemoryVersion",
    "MemoruleConfig",
    "MemoruleError",
    "PipelineResult",
    "PipelineStage",
    "PolicyConfig",
    "PolicyParseError",
    "RetrievalQuery",
    "RetrievalResult",
    "SimilarMemory",
    "StageExecutionError",
    "VectorStore",
    "load_config",
    "load_policy",
]
