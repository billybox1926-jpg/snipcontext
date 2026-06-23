"""Search domain CLI commands."""

from __future__ import annotations

import logging

import typer
from rich.box import ASCII as ASCII_BOX
from rich.console import Console
from rich.table import Table

from snipcontext.cli.context import get_context as _get_context
from snipcontext.cli.snippets import _print_snippet
from snipcontext.core.search_history import SearchHistoryStore

logger = logging.getLogger(__name__)
console = Console()

_history_store: SearchHistoryStore | None = None


def _get_history() -> SearchHistoryStore:
    global _history_store
    if _history_store is None:
        _history_store = SearchHistoryStore()
    return _history_store


def register_commands(app: typer.Typer) -> None:
    """Register search and index commands."""
    app.command()(search)
    app.command()(index)
    app.command("build-index")(build_index)


def search(
    queries: list[str] = typer.Argument(
        None,
        help="Search query(ies). Multiple queries trigger multi-search merge. Use query^N for weight (e.g. http^2).",
    ),
    mode: str = typer.Option(
        "hybrid", "--mode", "-m", help="Search mode: semantic, keyword, hybrid, tag"
    ),
    top_k: int = typer.Option(10, "--limit", "-n", help="Max results"),
    index: bool = typer.Option(False, "--index", "-i", help="Force reindex before search"),
    threshold: float = typer.Option(
        None, "--threshold", "-t", help="Minimum relevance score (0.0-1.0)"
    ),
    fuzzy: bool = typer.Option(False, "--fuzzy", help="Enable fuzzy matching for keyword search"),
    no_semantic: bool = typer.Option(
        False, "--no-semantic", help="Skip semantic search; use keyword-only mode"
    ),
    lang: str = typer.Option(
        None, "--lang", "-l", help="Filter by language (comma-separated, e.g. python,typescript)"
    ),
    tag: str = typer.Option(
        None, "--tag", help="Filter by tags (comma-separated, AND logic, e.g. cli,api)"
    ),
    boost_recent: bool = typer.Option(
        False, "--boost-recent", help="Weight newer snippets higher in rankings"
    ),
    explain: bool = typer.Option(False, "--explain", help="Show scoring breakdown for each result"),
    group_by: str = typer.Option(
        None, "--group-by", help="Group results: language, tag, or source"
    ),
) -> None:
    """Search snippets with semantic + keyword hybrid search.

    Accepts one or more queries.  When multiple queries are given they are
    merged using weighted Reciprocal Rank Fusion (RRF).  Append ``^N`` to
    a query to give it N-times weight, e.g. ``"http^2" "error"``.

    Use --group-by to organise results by language, tag, or source.
    """
    if not queries:
        console.print("[red]Error: QUERIES are required for search.[red]")
        raise typer.Exit(1)

    config, storage, searcher = _get_context()
    if index or not searcher.indices_ready:
        console.print("[yellow]Building search index...[/yellow]")
        snippets = storage.list_all()
        if not snippets:
            console.print("[yellow]No snippets to index. Add some first with `sc add`.[/yellow]")
            raise typer.Exit(0)
        searcher.index_snippets(snippets)
        console.print(f"[green]Indexed {len(snippets)} snippets[/green]")

    # Parse filter flags
    lang_list = [item.strip() for item in lang.split(",") if item.strip()] if lang else None
    tag_list = [t.strip() for t in tag.split(",") if t.strip()] if tag else None

    # Decide single-query vs multi-query
    if len(queries) == 1:
        results = searcher.search(
            queries[0],
            top_k=top_k,
            mode=mode,
            min_score=threshold,
            fuzzy=fuzzy,
            no_semantic=no_semantic,
            lang_filter=lang_list,
            tag_filter=tag_list,
            boost_recent=boost_recent,
            explain=explain,
        )
        query_label = queries[0]
    else:
        results = searcher.multi_search(
            queries,
            top_k=top_k,
            mode=mode,
            min_score=threshold,
            fuzzy=fuzzy,
            no_semantic=no_semantic,
            lang_filter=lang_list,
            tag_filter=tag_list,
            boost_recent=boost_recent,
            explain=explain,
        )
        query_label = ", ".join(queries)

    # Record query in search history
    store = _get_history()
    store.add(query_label, len(results))

    if not results:
        console.print(f"[yellow]No results for '{query_label}'[/yellow]")
        if not fuzzy:
            console.print("[dim]Try with --fuzzy for approximate matching[/dim]")
        if threshold and threshold > 0.1:
            console.print(f"[dim]Try lowering --threshold (currently {threshold})[/dim]")
        if lang_list or tag_list:
            console.print("[dim]Try removing --lang or --tag filters to broaden results[/dim]")
        raise typer.Exit(0)

    # Grouped output
    if group_by:
        groups = searcher.group_results(results, group_by=group_by)
        if not groups:
            console.print(f"[yellow]No grouped results for '{query_label}'[/yellow]")
            raise typer.Exit(0)

        console.print(
            f"\n[bold]{len(results)} results[/bold] for "
            f"'[cyan]{query_label}[/cyan]' "
            f"([dim]{mode}, grouped by {group_by}[/dim]):\n"
        )
        for group_key, group_results in groups.items():
            console.print(f"[bold]## {group_key}[/bold] ({len(group_results)} results)")
            for i, result in enumerate(group_results, 1):
                console.print(
                    f"  [yellow]{i}.[/yellow] "
                    f"[cyan]{result.snippet.metadata.title}[/cyan] "
                    f"[dim](score: {result.score:.3f})[/dim]"
                )
                if explain and result.explanation:
                    console.print(
                        f"    [dim]rrf: {result.explanation.get('rrf_score', 'N/A')}[/dim]"
                    )
            console.print()
    else:
        # Flat output
        console.print(
            f"\n[bold]{len(results)} results[/bold] for '[cyan]{query_label}[/cyan]' ([dim]{mode}[/dim]):\n"
        )
        for i, result in enumerate(results, 1):
            _print_snippet(result.snippet, score=result.score, idx=i)
            if explain and result.explanation:
                console.print("  [dim]── explain ──[/dim]")
                for key, val in result.explanation.items():
                    console.print(f"  [dim]{key}: {val}[/dim]")
            console.print()


def _show_history(store: SearchHistoryStore) -> None:
    entries = store.get_recent(limit=50)
    if not entries:
        console.print("[dim]No search history yet.[/dim]")
        return
    table = Table(title="Search History", box=ASCII_BOX)
    table.add_column("ID", style="cyan", justify="right")
    table.add_column("Query")
    table.add_column("Time", style="dim")
    table.add_column("Results", justify="right")
    table.add_column("Fav", justify="center")
    for entry in entries:
        ts = entry.timestamp.strftime("%Y-%m-%d %H:%M")
        fav = "★" if entry.is_favorite else ""
        table.add_row(str(entry.id), entry.query, ts, str(entry.result_count), fav)
    console.print(table)


def _show_favorites(store: SearchHistoryStore) -> None:
    entries = store.get_favorites()
    if not entries:
        console.print("[dim]No favorites yet. Use --favorite <id> to mark one.[/dim]")
        return
    table = Table(title="Favorite Searches", box=ASCII_BOX)
    table.add_column("ID", style="cyan", justify="right")
    table.add_column("Query")
    table.add_column("Time", style="dim")
    table.add_column("Results", justify="right")
    for entry in entries:
        ts = entry.timestamp.strftime("%Y-%m-%d %H:%M")
        table.add_row(str(entry.id), entry.query, ts, str(entry.result_count))
    console.print(table)


def _toggle_favorite(store: SearchHistoryStore, entry_id: int) -> None:
    entry = store.get_by_id(entry_id)
    if not entry:
        console.print(f"[red]No history entry with ID {entry_id}[/red]")
        raise typer.Exit(1)
    is_fav = store.toggle_favorite(entry_id)
    label = "favorited" if is_fav else "unfavorited"
    console.print(f"[green]{label}: '{entry.query}' (ID {entry_id})[/green]")


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
