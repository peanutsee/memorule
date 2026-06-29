# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0-beta.6] - 2026-06-26

### Added

- **`prompts` config in `memorule.yaml`** — customizable global and per-stage system prompts
  (`PromptConfig`, `structured_output`: `auto` | `always` | `never`).
- **`StructuredLanguageModel` protocol** and **`invoke_structured()`** helper with automatic
  fallback to JSON parse + Pydantic validation for text-only providers.
- **PR CI workflow** — pytest, ruff, and mypy on push/PR to `main`.
- **Docs:** single-agent and multi-agent deployment patterns in [Usage guide](docs/usage.md).

### Changed

- All six LLM stages use `invoke_structured` and configured system prompts instead of a
  hardcoded `SYSTEM_PROMPT`.
- User prompt builders no longer embed `Respond with JSON: {...}` blocks; schema hints are
  added on the fallback path only.
- `MemoryEngine`, `PipelineContext`, and `MemoryRetriever` accept `prompts: PromptConfig`.
- `__version__` is read from package metadata (synced with `pyproject.toml`).
- Scaffold `memorule.yaml` and LLM provider example updated for prompts and optional
  `complete_structured`.

### Exported

- `PromptConfig`, `StructuredOutputMode`, `StructuredLanguageModel` from `memorule`.

## [1.0.0-beta.5] - 2026-06-26

### Changed

- **`Memory.type` is optional** (`str | None`); no fixed taxonomy (`preference`, `fact`, etc.).
- Default policy and scaffold use **generic agent memory** language instead of food-specific examples.
- Persistence omits `type` from vector metadata when null.

## [1.0.0-beta.4] - 2026-06-26

### Added

- **`Interaction.user_content` / `assistant_content`** — policy evaluation focuses on user text;
  assistant replies are context only.
- **Pre-extraction vector search** before memory extraction to surface related existing memories.
- Optional **`extraction` policy section** for fidelity rules (preserve specifics, concrete summaries).

### Changed

- Hardened extraction and policy prompts to reduce vague summaries and missed preferences.
- Vector store metadata includes truncated `content` preview for debugging.

## [1.0.0-beta.3] - 2026-06-26

### Added

- **[Setup guide](docs/setup.md)** and **[Usage guide](docs/usage.md)**.
- Demo screenshots in README (food chat agent, Pinecone memory search).

## [1.0.0-beta.2] - 2026-06-26

### Fixed

- **`memory_extraction` validation error** when the LLM returned a dict/list for `content` instead
  of a string — values are coerced to JSON strings via Pydantic validators.

### Changed

- Hardened extraction prompt to request prose `content`.

## [1.0.0-beta.1] - 2026-06-26

### Added

- Initial public beta: memory pipeline, policy-driven stages, protocols, CLI (`memorule init`,
  `policy wizard`, `validate`), hooks, retrieval, and explainability traces.

[1.0.0-beta.6]: https://github.com/peanutsee/memorule/compare/v1.0.0-beta.5...v1.0.0-beta.6
[1.0.0-beta.5]: https://github.com/peanutsee/memorule/compare/v1.0.0-beta.4...v1.0.0-beta.5
[1.0.0-beta.4]: https://github.com/peanutsee/memorule/compare/v1.0.0-beta.3...v1.0.0-beta.4
[1.0.0-beta.3]: https://github.com/peanutsee/memorule/compare/v1.0.0-beta.2...v1.0.0-beta.3
[1.0.0-beta.2]: https://github.com/peanutsee/memorule/compare/v1.0.0-beta.1...v1.0.0-beta.2
[1.0.0-beta.1]: https://github.com/peanutsee/memorule/releases/tag/v1.0.0-beta.1
