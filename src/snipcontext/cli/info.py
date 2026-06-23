"""Show current storage configuration."""

from __future__ import annotations

import typer
from rich.box import ASCII as ASCII_BOX
from rich.console import Console
from rich.table import Table

from snipcontext.config.paths import get_config_path, get_storage_root, is_project_local
from snipcontext.config.settings import get_config

console = Console()


def register_commands(app: typer.Typer) -> None:
    """Register info commands."""

    @app.command("info")  # type: ignore[untyped-decorator]
    def info() -> None:
        """Show the current storage root and configuration."""
        root = get_storage_root()
        config_path = get_config_path()
        project_local = is_project_local()
        config = get_config()

        mode = "project-local" if project_local else "global"

        table = Table(title="SnipContext Configuration", box=ASCII_BOX)
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Mode", mode)
        table.add_row("Storage root", str(root))
        table.add_row("Snippets dir", str(config.snippets_path))
        table.add_row("Index dir", str(config.index_path))
        table.add_row("Config file", str(config_path))

        console.print(table)
