"""Search domain CLI commands."""

import logging

import typer
from rich.console import Console

from snipcontext.cli.context import get_context as _get_context
from snipcontext.cli.snippets import _print_snippet

logger = logging.getLogger(__name__)
console = Console()


def register_commands(app: typer.Typer) -> None:
    """Register search and index commands."""
    app.command()(search)
    app.command()(index)
    app.command("build-index")(build_index)


def search(
    query: str = typer.Argument(..., help="Search query"),
    mode: str = typer.Option(
        "hybrid", "--mode", "-m", help="Search mode: semantic, keyword, hybrid, tag"
    ),
    top_k: int = typer.Option(10, "--limit", "-n", help="Max results"),
    index: bool = typer.Option(False, "--index", "-i", help="Force reindex before search"),
    threshold: float = typer.Option(
        None, "--threshold", "-t", help="Minimum relevance score (0.0-1.0)"
    ),
    fuzzy: bool = typer.Option(False, "--fuzzy", help="Enable fuzzy matching for keyword search"),
) -> None:
    """Search snippets with semantic + keyword hybrid search."""
    config, storage, searcher = _get_context()
    if index or not searcher.indices_ready:
        console.print("[yellow]Building search index...[/yellow]")
        snippets = storage.list_all()
        if not snippets:
            console.print("[yellow]No snippets to index. Add some first with `sc add`.[/yellow]")
            raise typer.Exit(0)
        searcher.index_snippets(snippets)
        console.print(f"[green]Indexed {len(snippets)} snippets[/green]")
    results = searcher.search(query, top_k=top_k, mode=mode, min_score=threshold, fuzzy=fuzzy)
    if not results:
        console.print(f"[yellow]No results for '{query}'[/yellow]")
        if not fuzzy:
            console.print("[dim]Try with --fuzzy for approximate matching[/dim]")
        if threshold and threshold > 0.1:
            console.print(f"[dim]Try lowering --threshold (currently {threshold})[/dim]")
        raise typer.Exit(0)
    console.print(
        f"\n[bold]{len(results)} results[/bold] for '[cyan]{query}[/cyan]' ([dim]{mode}[/dim]):\n"
    )
    for i, result in enumerate(results, 1):
        _print_snippet(result.snippet, score=result.score, idx=i)
        console.print()


def index(
    force: bool = typer.Option(False, "--force", help="Skip confirmation prompt"),
) -> None:
    """Rebuild the search index from all stored snippets."""
    config, storage, search = _get_context()
    snippets = storage.list_all()
    if not snippets:
        console.print("[yellow]No snippets found. Index will be empty.[/yellow]")
        if not force:
            return
    console.print(f"Indexing {len(snippets)} snippets...")
    search.index_snippets(snippets)
    console.print(f"Index complete. {len(snippets)} snippets indexed.")


def build_index(
    force: bool = typer.Option(False, "--force", "-f", help="Force rebuild even if index exists"),
) -> None:
    """Build or rebuild the semantic search index."""
    config, storage, searcher = _get_context()
    snippets = storage.list_all()
    if not snippets:
        console.print("[yellow]No snippets found. Add some first![/yellow]")
        return
    if not force and searcher.indices_ready:
        console.print(
            f"[yellow]Index already exists ({len(snippets)} snippets). Use --force to rebuild.[/yellow]"
        )
        return
    console.print(f"Building index for {len(snippets)} snippets...")
    searcher.index_snippets(snippets)
    console.print(f"[green]Index complete. {len(snippets)} snippets indexed.[/green]")
