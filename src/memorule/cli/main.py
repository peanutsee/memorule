"""Memorule CLI entrypoint (Typer)."""

from __future__ import annotations

from pathlib import Path

import typer

from memorule.cli import scaffold
from memorule.cli.init import run_init
from memorule.cli.policy_wizard import run_wizard
from memorule.cli.validate import run_validate

app = typer.Typer(
    help="Memorule — rule-first, model-agnostic memory orchestration.",
    no_args_is_help=True,
)
policy_app = typer.Typer(help="Policy management commands.", no_args_is_help=True)
hooks_app = typer.Typer(help="Hook scaffolding commands.", no_args_is_help=True)
app.add_typer(policy_app, name="policy")
app.add_typer(hooks_app, name="hooks")


@app.command()
def init(
    directory: str = typer.Argument("memorule", help="Target config directory."),
    force: bool = typer.Option(False, "--force", help="Overwrite existing files."),
) -> None:
    """Scaffold project artifacts (config, policy, provider stubs, hooks)."""
    typer.echo(run_init(directory, force=force))


@policy_app.command("wizard")
def policy_wizard(
    policy_path: str = typer.Option(
        "memorule/policy/policy.yaml", "--path", help="Policy file to write."
    ),
    section: str | None = typer.Option(None, "--section", help="Update a single section."),
    non_interactive: str | None = typer.Option(
        None, "--non-interactive", help="JSON file of answers for CI."
    ),
) -> None:
    """Interactively generate or update policy.yaml."""
    typer.echo(run_wizard(policy_path, section=section, non_interactive=non_interactive))


@app.command()
def validate(
    config_path: str = typer.Argument("memorule/memorule.yaml", help="Config file path."),
    check_providers: bool = typer.Option(
        False, "--check-providers", help="Verify provider modules are importable."
    ),
) -> None:
    """Validate config + policy without calling external services."""
    ok, messages = run_validate(config_path, check_providers=check_providers)
    for message in messages:
        typer.echo(message)
    if not ok:
        raise typer.Exit(code=1)


@hooks_app.command("new")
def hooks_new(
    name: str = typer.Argument(..., help="Hook class name (e.g. Auditor)."),
    directory: str = typer.Option("memorule/hooks", "--dir", help="Hooks directory."),
) -> None:
    """Scaffold a custom PipelineStage hook file."""
    class_name = name[0].upper() + name[1:]
    target = Path(directory) / f"{class_name.lower()}.py"
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        typer.echo(f"Hook already exists: {target}")
        raise typer.Exit(code=1)
    target.write_text(scaffold.hook_template(class_name), encoding="utf-8")
    typer.echo(f"Created hook: {target}")


if __name__ == "__main__":
    app()
