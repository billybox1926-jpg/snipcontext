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
    queries: list[str] = typer.Argument(..., help="Search query(ies). Multiple queries trigger multi-search merge. Use query^N for weight (e.g. http^2)."),
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
    explain: bool = typer.Option(
        False, "--explain", help="Show scoring breakdown for each result"
    ),
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
    lang_list = [l.strip() for l in lang.split(",") if l.strip()] if lang else None
    tag_list = [t.strip() for t in tag.split(",") if t.strip()] if tag else None

    # Decide single-query vs multi-query
    common_kwargs = dict(
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

    if len(queries) == 1:
        # Single query — use the fast path
        results = searcher.search(queries[0], **common_kwargs)
        query_label = queries[0]
    else:
        # Multi-query — use RRF merge
        results = searcher.multi_search(queries, **common_kwargs)
        query_label = ", ".join(queries)

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
                    console.print(f"    [dim]rrf: {result.explanation.get('rrf_score', 'N/A')}[/dim]")
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
