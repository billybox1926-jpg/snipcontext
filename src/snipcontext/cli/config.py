"""Config domain CLI commands."""

import logging

import typer
from rich.console import Console
from rich.panel import Panel

from snipcontext.cli.context import get_context as _get_context
from snipcontext.core.config_ops import get_config_paths, get_config_values

logger = logging.getLogger(__name__)
console = Console()


def register_commands(app: typer.Typer) -> None:
    """Register config commands."""

    @app.command("show")
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

    @app.command("init")
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

    @app.command("path")
    def config_path() -> None:
        """Show configuration and data directories."""
        config, _, _ = _get_context()
        paths = get_config_paths(config)
        console.print(f"[bold]Config file:[/bold]  {paths['config_file']}")
        console.print(f"[bold]Data dir:[/bold]     {paths['data_dir']}")
        console.print(f"[bold]Snippets:[/bold]    {paths['snippets']}")
        console.print(f"[bold]Index:[/bold]       {paths['index']}")
