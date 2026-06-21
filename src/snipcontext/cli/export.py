"""Export domain CLI commands."""

import logging
from pathlib import Path

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table

from snipcontext.cli.context import get_context as _get_context
from snipcontext.core.models import Snippet
from snipcontext.plugins.base import PluginManager

logger = logging.getLogger(__name__)
console = Console()


def register_commands(app: typer.Typer) -> None:
    """Register export and provider commands."""

    @app.command()  # type: ignore[untyped-decorator]
    def export(
        query: str | None = typer.Option(None, "--query", "-q", help="Export search results"),
        ids: list[str] = typer.Option([], "--id", help="Export specific snippet IDs"),
        provider: str = typer.Option("generic", "--provider", "-p", help="Export format provider"),
        output: str | None = typer.Option(None, "--output", "-o", help="Output file (default: stdout)"),
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
        if output:
            Path(output).write_text(formatted)
            console.print(f"[green]Exported {len(snippets)} snippets to {output}[/green]")
        else:
            console.print(Markdown(formatted))

    @app.command()  # type: ignore[untyped-decorator]
    def providers() -> None:
        """List available export providers."""
        pm = PluginManager()
        pm.load_builtin_providers()
        table = Table(title="Export Providers", show_header=True)
        table.add_column("Name", style="cyan")
        table.add_column("Description", style="white")
        table.add_column("Format", style="green")
        for name, desc in pm.list_providers().items():
            fmt = pm._providers.get(name)
            fmt_name = fmt.format if fmt and hasattr(fmt, "format") else "?"
            table.add_row(name, desc, str(fmt_name))
        console.print(table)
