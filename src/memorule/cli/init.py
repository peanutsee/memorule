"""`memorule init` — scaffold project artifacts."""

from __future__ import annotations

from pathlib import Path

from memorule.cli import scaffold

NEXT_STEPS = """\
Memorule initialized at: {root}

Next steps:
  1. Implement provider stubs in {root}/providers/ (rename *.py.example -> *.py)
  2. Run `memorule policy wizard` to customize your memory rules
  3. Run `memorule validate` to check your configuration
  4. Wire MemoryEngine + ContextBuilder in your agent (see README)
"""


def _write(path: Path, content: str, *, force: bool) -> bool:
    if path.exists() and not force:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def run_init(directory: str = "memorule", *, force: bool = False) -> str:
    root = Path(directory)

    if root.exists() and any(root.iterdir()) and not force:
        return (
            f"Directory '{root}' already exists and is not empty. "
            "Re-run with --force to overwrite."
        )

    files = {
        root / "memorule.yaml": scaffold.MEMORULE_YAML,
        root / "policy" / "policy.yaml": scaffold.POLICY_YAML,
        root / "providers" / "llm.py.example": scaffold.LLM_PROVIDER,
        root / "providers" / "embeddings.py.example": scaffold.EMBEDDINGS_PROVIDER,
        root / "providers" / "stores.py.example": scaffold.STORES_PROVIDER,
        root / "hooks" / "__init__.py": scaffold.HOOKS_INIT,
        root / "hooks" / "example_auditor.py": scaffold.EXAMPLE_HOOK,
    }

    written = 0
    for path, content in files.items():
        if _write(path, content, force=force):
            written += 1

    return NEXT_STEPS.format(root=root)
