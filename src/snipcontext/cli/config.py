"""Config domain CLI commands."""

from __future__ import annotations

import logging

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.box import ASCII as ASCII_BOX

from snipcontext.cli.context import get_context as _get_context
from snipcontext.core.config_ops import get_config_paths, get_config_values

logger = logging.getLogger(__name__)
console = Console()


def _set_nested(config, dotted: str, value: str):
    parts = dotted.split(".")
    if len(parts) < 2:
        raise typer.BadParameter(f"Expected dotted path like 'search.index_type', got {dotted!r}")
    section = getattr(config, parts[0])
    target = section
    for part in parts[1:-1]:
        target = getattr(target, part)
    key = parts[-1]
    if not hasattr(target, key):
        raise typer.BadParameter(f"Unknown config key: {dotted!r}")
    field_info = type(target).model_fields.get(key)
    target_type = field_info.annotation if field_info else str
    typed_value: str | bool | int | float = value
    if target_type is bool:
        if value.lower() in {"true", "1", "yes"}:
            typed_value = True
        elif value.lower() in {"false", "0", "no"}:
            typed_value = False
        else:
            raise typer.BadParameter(f"Bool expected for {dotted!r}, got {value!r}")
    elif target_type is int:
        typed_value = int(value)
    elif target_type is float:
        typed_value = float(value)
    setattr(target, key, typed_value)


def register_commands(app: typer.Typer) -> None:
    """Register config commands."""

    @app.command("show")  # type: ignore[untyped-decorator]
    def config_show() -> None:
        """Show current configuration."""
        config, _, _ = _get_context()
        payload = get_config_values(config)
        import yaml

        console.print(
            Panel(
                yaml.safe_dump(payload, default_flow_style=False, sort_keys=False),
                title="Configuration",
                border_style="blue",
            )
        )
        console.print(f"\n[dim]Config file: {config.config_file_path}[/dim]")

    @app.command("init")  # type: ignore[untyped-decorator]
    def config_init(
        force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing config"),
    ) -> None:
        """Initialize configuration file with defaults."""
        config, _, _ = _get_context()
        if config.config_file_path.exists() and not force:
            console.print(f"[yellow]Config already exists at {config.config_file_path}[/yellow]")
            console.print("Use --force to overwrite.")
            return
        config.save_to_file()
        console.print(f"[green]Configuration written to:[/green] {config.config_file_path}")

    @app.command("path")  # type: ignore[untyped-decorator]
    def config_path() -> None:
        """Show configuration and data directories."""
        config, _, _ = _get_context()
        paths = get_config_paths(config)
        console.print(f"[bold]Config file:[/bold]  {paths['config_file']}")
        console.print(f"[bold]Data dir:[/bold]     {paths['data_dir']}")
        console.print(f"[bold]Snippets:[/bold]    {paths['snippets']}")
        console.print(f"[bold]Index:[/bold]       {paths['index']}")

    @app.command("set")  # type: ignore[untyped-decorator]
    def config_set(
        key: str = typer.Argument(..., help="Dotted config key (e.g. search.index_type)"),
        value: str = typer.Argument(..., help="Value to assign"),
        save: bool = typer.Option(True, "--save/--no-save", help="Persist to config file"),
    ) -> None:
        """Update a config value for the current session."""
        config, _, _ = _get_context()
        try:
            _set_nested(config, key, value)
        except typer.BadParameter:
            raise
        except Exception as exc:
            raise typer.BadParameter(str(exc)) from exc
        if save:
            config.save_to_file()
        console.print(
            f"[green]Set[/green] {key} = {getattr(config, key.split('.')[0]).model_dump().get(key.split('.')[-1], value)}"
        )

    @app.command("list")  # type: ignore[untyped-decorator]
    def config_list() -> None:
        """List available configuration keys."""
        config, _, _ = _get_context()
        payload = get_config_values(config)
        rows: list[tuple[str, str, str]] = []
        for name, model in payload.items():
            rows.append((name, type(model).__name__, ""))
            if isinstance(model, dict):
                for key, value in model.items():
                    if key.startswith("_"):
                        continue
                    rows.append((f"  {name}.{key}", type(value).__name__, ""))
        table = Table(title="Configuration keys", box=ASCII_BOX)
        table.add_column("Key", style="cyan")
        table.add_column("Type", style="magenta")
        table.add_column("Default", style="green")
        for row in rows:
            table.add_row(*row)
        console.print(table)
        console.print(f"\n[dim]Config file: {config.config_file_path}[/dim]")
