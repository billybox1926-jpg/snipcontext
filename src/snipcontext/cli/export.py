"""Export domain CLI commands."""

import logging
from pathlib import Path

import typer
from rich.box import ASCII as ASCII_BOX
from rich.console import Console
from rich.table import Table

from snipcontext.cli.context import get_context as _get_context
from snipcontext.core.models import Snippet
from snipcontext.plugins.base import PluginManager
from snipcontext.plugins.registry import PluginRegistry

logger = logging.getLogger(__name__)
console = Console()


def register_commands(app: typer.Typer) -> None:
    """Register export and provider commands."""

    @app.command()  # type: ignore[untyped-decorator]
    def export(
        query: str | None = typer.Option(None, "--query", "-q", help="Export search results"),
        ids: list[str] = typer.Option([], "--id", help="Export specific snippet IDs"),
        provider: str = typer.Option("generic", "--provider", "-p", help="Export format provider"),
        output: str | None = typer.Option(
            None, "--output", "-o", help="Output file (default: stdout)"
        ),
        top_k: int = typer.Option(10, "--limit", "-n", help="Max results for query export"),
    ) -> None:
        """Export snippets in LLM-optimized format."""
        config, storage, searcher = _get_context()
        pm = PluginManager()
        pm.load_builtin_providers()
        try:
            prov = pm.get_provider(provider)
        except KeyError as err:
            console.print(f"[red]Unknown provider: {provider}[/red]")
            console.print(f"Available: {', '.join(pm.list_providers().keys())}")
            raise typer.Exit(1) from err
        snippets: list[Snippet] = []
        if ids:
            for sid in ids:
                try:
                    snippets.append(storage.get(sid))
                except Exception:
                    console.print(f"[yellow]Warning: snippet not found: {sid}[/yellow]")
        elif query:
            if not searcher.indices_ready:
                all_s = storage.list_all()
                if all_s:
                    searcher.index_snippets(all_s)
            results = searcher.search(query, top_k=top_k)
            snippets = [r.snippet for r in results]
        else:
            snippets = storage.list_all()
        if not snippets:
            console.print("[yellow]No snippets to export.[/yellow]")
            return
        formatted = prov.export_batch(snippets)
        if output and output != "-":
            Path(output).write_text(formatted)
            console.print(f"[green]Exported {len(snippets)} snippets to {output}[/green]")
        else:
            console.print(formatted, markup=False)

    @app.command()  # type: ignore[untyped-decorator]
    def providers(
        health: bool = typer.Option(False, "--health", help="Run provider health checks"),
    ) -> None:
        """List available export providers.

        Use --health to run a health check on each provider.
        """
        pm = PluginManager()
        pm.load_builtin_providers()
        if health:
            if not pm.list_providers():
                console.print("[yellow]No providers registered.[/yellow]")
                raise typer.Exit(1)
            table = Table(title="Provider Health", show_header=True, box=ASCII_BOX)
            table.add_column("Name", style="cyan")
            table.add_column("Status", style="green")
            table.add_column("Error", style="red")
            for name, provider_cls in pm._providers.items():
                try:
                    provider = provider_cls()
                    status = provider.health_check()
                    error = ""
                except Exception as exc:
                    status = "error"
                    error = str(exc)
                table.add_row(name, status, error)
            console.print(table)
            return
        table = Table(title="Export Providers", show_header=True, box=ASCII_BOX)
        table.add_column("Name", style="cyan")
        table.add_column("Description", style="white")
        table.add_column("Format", style="green")
        for name, desc in pm.list_providers().items():
            fmt = pm._providers.get(name)
            fmt_name = fmt.format if fmt and hasattr(fmt, "format") else "?"
            table.add_row(name, desc, str(fmt_name))
        console.print(table)

    @app.command()  # type: ignore[untyped-decorator]
    def plugins(
        list_cmd: bool = typer.Option(False, "--list", help="List loaded plugins"),
        health: bool = typer.Option(False, "--health", help="Run plugin/provider health checks"),
        load_name: str | None = typer.Option(None, "--load", help="Load a plugin by name."),
        unload_name: str | None = typer.Option(None, "--unload", help="Unload a plugin by name."),
    ) -> None:
        """Plugin management commands."""
        actions = sum(1 for x in (list_cmd, health, load_name, unload_name) if x)
        if actions > 1:
            console.print(
                "[red]Error: Use only one of --list, --health, --load NAME, or --unload NAME[/red]",
                err=True,
            )
            raise typer.Exit(1)

        pm = PluginManager()
        pm.load_builtin_providers()
        registry = PluginRegistry()

        if load_name:
            try:
                registry.load_plugin(load_name)
                console.print(f"[green]Loaded plugin '{load_name}'[/green]")
            except ValueError as e:
                console.print(f"[red]Error: {e}[/red]", err=True)
                raise typer.Exit(1)
            return

        if unload_name:
            try:
                registry.unload_plugin(unload_name)
                console.print(f"[green]Unloaded plugin '{unload_name}'[/green]")
            except ValueError as e:
                console.print(f"[red]Error: {e}[/red]", err=True)
                raise typer.Exit(1)
            return

        if health:
            if not pm.list_providers():
                console.print("[yellow]No providers registered.[/yellow]")
                raise typer.Exit(1)
            table = Table(title="Provider Health", show_header=True, box=ASCII_BOX)
            table.add_column("Name", style="cyan")
            table.add_column("Status", style="green")
            table.add_column("Error", style="red")
            for name in list(pm.list_providers().keys()):
                try:
                    provider = registry.get_provider(name)
                    status = provider.health_check()
                    error = ""
                except Exception as exc:
                    status = "error"
                    error = str(exc)
                table.add_row(name, status, error)
            console.print(table)
            return

        if list_cmd:
            if not pm.plugins:
                console.print("[yellow]No plugins registered.[/yellow]")
                return
            table = Table(title="Plugins", show_header=True, box=ASCII_BOX)
            table.add_column("Name", style="cyan")
            table.add_column("Version", style="green")
            table.add_column("API", style="blue")
            table.add_column("Status", style="white")
            for manifest in pm.list_plugins():
                table.add_row(
                    manifest.name,
                    manifest.version,
                    manifest.api_version,
                    "loaded",
                )
            console.print(table)
            return

        console.print("Use --list, --health, --load NAME, or --unload NAME")
        raise typer.Exit(0)
