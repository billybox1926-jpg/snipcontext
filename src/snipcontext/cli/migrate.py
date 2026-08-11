"""Migrate snippets, config, and indexes to the current version."""

from __future__ import annotations

from pathlib import Path

import typer

from snipcontext.cli.context import get_context as _get_context

migrate_app = typer.Typer(name="migrate", help="Migrate snippets, config, and indexes")


@migrate_app.command("check")  # type: ignore[untyped-decorator]
def migrate_check() -> None:
    """Check whether the storage version needs migration."""
    _, _, search = _get_context()
    from snipcontext.core.storage import StorageEngine

    storage = StorageEngine()
    current = storage.read_storage_version()
    expected = storage.expected_version

    if current == expected:
        typer.echo(f"Storage is already at version {current}.")
        raise typer.Exit()

    typer.echo(f"Storage version {current} is behind expected version {expected}.")
    typer.echo("Run `snipcontext migrate --dry-run` for next steps.")


@migrate_app.command()  # type: ignore[untyped-decorator]
def migrate(
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would be done without making changes"
    ),
    backup_path: Path = typer.Option(
        None, "--backup-path", help="Path to store a backup before migration"
    ),
) -> None:
    """Migrate snippets, config, and indexes to the current version."""
    typer.echo("Automatic migration is not yet implemented.")
    typer.echo("Please backup your snippets and manually upgrade following docs/MIGRATION.md.")
    if dry_run:
        typer.echo("Dry run - no changes made.")
        raise typer.Exit(code=0)
    raise typer.Exit(code=1)


def register_commands(app: typer.Typer) -> None:
    """Register migration commands."""
    app.add_typer(migrate_app)
