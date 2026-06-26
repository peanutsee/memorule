"""Memorule exception hierarchy."""


class MemoruleError(Exception):
    """Base exception for all memorule errors."""


class PolicyParseError(MemoruleError):
    """LLM returned unparseable JSON."""

    def __init__(self, message: str, *, raw_output: str | None = None, stage: str | None = None):
        super().__init__(message)
        self.raw_output = raw_output
        self.stage = stage


class StageExecutionError(MemoruleError):
    """Stage failure with stage name and context."""

    def __init__(self, message: str, *, stage: str, cause: Exception | None = None):
        super().__init__(message)
        self.stage = stage
        self.cause = cause


class MemoryNotFoundError(MemoruleError):
    """Referenced memory ID missing."""

    def __init__(self, memory_id: str):
        super().__init__(f"Memory not found: {memory_id}")
        self.memory_id = memory_id


class ConfigError(MemoruleError):
    """Invalid configuration file."""
