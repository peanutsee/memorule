"""Memorule: rule-first, model-agnostic long-term memory orchestration."""

from importlib.metadata import PackageNotFoundError, version

from memorule.config import MemoruleConfig, PromptConfig, StructuredOutputMode, load_config
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
from memorule.protocols import EmbeddingModel, LanguageModel, MemoryStore, StructuredLanguageModel, VectorStore
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

try:
    __version__ = version("memorule")
except PackageNotFoundError:
    __version__ = "0.0.0+dev"

__all__ = [
    "__version__",
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
    "PromptConfig",
    "RetrievalQuery",
    "RetrievalResult",
    "SimilarMemory",
    "StageExecutionError",
    "StructuredLanguageModel",
    "StructuredOutputMode",
    "VectorStore",
    "load_config",
    "load_policy",
]
