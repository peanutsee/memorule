"""Core domain types for memorule."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


def _utcnow() -> datetime:
    return datetime.now(UTC)


def new_memory_id() -> str:
    return str(uuid4())


class MemoryDecision(StrEnum):
    STORE = "store"
    DISCARD = "discard"
    MERGE = "merge"
    UPDATE = "update"
    VERSION = "version"


class ContextFormat(StrEnum):
    MARKDOWN = "markdown"
    XML = "xml"
    PLAIN = "plain"


class Interaction(BaseModel):
    model_config = ConfigDict(extra="allow")

    content: str
    user_content: str | None = None
    assistant_content: str | None = None
    role: str | None = None
    timestamp: datetime = Field(default_factory=_utcnow)
    source: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class MemoryVersion(BaseModel):
    model_config = ConfigDict(extra="allow")

    content: str
    summary: str | None = None
    version: int
    changed_at: datetime = Field(default_factory=_utcnow)
    reason: str | None = None


class Memory(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str = Field(default_factory=new_memory_id)
    type: str = "fact"
    content: str
    summary: str | None = None
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
    version: int = 1
    confidence: float = 1.0
    source: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SimilarMemory(BaseModel):
    memory: Memory
    similarity: float


class StageExplanation(BaseModel):
    step: str
    decision: str | None = None
    reason: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class ExplainabilityTrace(BaseModel):
    steps: list[StageExplanation] = Field(default_factory=list)

    def add(
        self,
        step: str,
        *,
        decision: str | None = None,
        reason: str | None = None,
        **details: Any,
    ) -> None:
        self.steps.append(
            StageExplanation(step=step, decision=decision, reason=reason, details=details)
        )

    def format(self) -> str:
        lines = ["Decision trace:"]
        for step in self.steps:
            line = f"  [{step.step}]"
            if step.decision:
                line += f" {step.decision}"
            if step.reason:
                line += f" — {step.reason}"
            lines.append(line)
        return "\n".join(lines)


class PipelineResult(BaseModel):
    decision: MemoryDecision
    reason: str | None = None
    matched_policy: str | None = None
    memory: Memory | None = None
    merged_with: str | None = None
    confidence: float | None = None
    trace: ExplainabilityTrace = Field(default_factory=ExplainabilityTrace)

    @property
    def explanation(self) -> str:
        parts = [
            f"Decision:\n{self.decision.value.title()}",
        ]
        if self.reason:
            parts.append(f"\nReason:\n{self.reason}")
        if self.matched_policy:
            parts.append(f"\nMatched Policy:\n{self.matched_policy}")
        if self.memory:
            parts.append(f"\nExtracted Memory:\n{self.memory.content}")
        if self.merged_with:
            parts.append(f"\nMerged With:\n{self.merged_with}")
        if self.confidence is not None:
            parts.append(f"\nConfidence:\n{self.confidence}")
        parts.append(f"\n{self.trace.format()}")
        return "\n".join(parts)


class RetrievalQuery(BaseModel):
    content: str
    limit: int = 10
    min_confidence: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class RetrievalResult(BaseModel):
    memories: list[Memory]
    scores: list[float] = Field(default_factory=list)
    trace: ExplainabilityTrace = Field(default_factory=ExplainabilityTrace)


class MemoryContext(BaseModel):
    memories: list[Memory]
    formatted: str
    trace: ExplainabilityTrace = Field(default_factory=ExplainabilityTrace)
