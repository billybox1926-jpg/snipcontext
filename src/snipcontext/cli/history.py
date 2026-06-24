"""History and favorites CLI commands."""

from __future__ import annotations

import logging

import typer
from rich.box import ASCII as ASCII_BOX
from rich.console import Console
from rich.table import Table

from snipcontext.core.search_history import SearchHistoryStore

logger = logging.getLogger(__name__)
console = Console()

history_app = typer.Typer(
    name="history",
    help="Manage search history and favorites",
    no_args_is_help=True,
)


def register_commands(app: typer.Typer) -> None:
    """Register history commands on the root app."""
    app.add_typer(history_app)


@history_app.command("list")  # type: ignore[untyped-decorator]
def list_history(
    limit: int = typer.Option(10, "--limit", "-n", help="Number of recent entries to show"),
) -> None:
    """Show recent search history."""
    store = SearchHistoryStore()
    entries = store.get_recent(limit=limit)
    if not entries:
        console.print("[dim]No search history yet.[/dim]")
        raise typer.Exit(0)

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


@history_app.command("favorites")  # type: ignore[untyped-decorator]
def list_favorites() -> None:
    """Show favorite queries."""
    store = SearchHistoryStore()
    entries = store.get_favorites()
    if not entries:
        console.print("[dim]No favorites yet. Use 'sc history favorite <id>' to mark one.[/dim]")
        raise typer.Exit(0)

    table = Table(title="Favorite Searches", box=ASCII_BOX)
    table.add_column("ID", style="cyan", justify="right")
    table.add_column("Query")
    table.add_column("Time", style="dim")
    table.add_column("Results", justify="right")
    for entry in entries:
        ts = entry.timestamp.strftime("%Y-%m-%d %H:%M")
        table.add_row(str(entry.id), entry.query, ts, str(entry.result_count))
    console.print(table)


@history_app.command("favorite")  # type: ignore[untyped-decorator]
def toggle_favorite(
    entry_id: int = typer.Argument(..., help="History entry ID to toggle favorite status"),
) -> None:
    """Toggle favorite status on a history entry."""
    store = SearchHistoryStore()
    entry = store.get_by_id(entry_id)
    if not entry:
        console.print(f"[red]No history entry with ID {entry_id}[/red]")
        raise typer.Exit(1)
    is_fav = store.toggle_favorite(entry_id)
    label = "favorited" if is_fav else "unfavorited"
    console.print(f"[green]{label}: '{entry.query}' (ID {entry_id})[/green]")


@history_app.command("add")  # type: ignore[untyped-decorator]
def add_history(
    query: str = typer.Argument(..., help="Search query to add to history"),
    favorite: bool = typer.Option(False, "--favorite", help="Mark as favorite immediately"),
) -> None:
    """Add a query to history manually."""
    store = SearchHistoryStore()
    store.add(query, result_count=0)
    if favorite:
        entries = store.get_recent(limit=1)
        if entries and entries[0].query == query:
            store.toggle_favorite(entries[0].id)
    console.print(f"[green]Added '{query}' to history.[/green]")


@history_app.command("clear")  # type: ignore[untyped-decorator]
def clear_history(
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation prompt"),
) -> None:
    """Clear all search history."""
    store = SearchHistoryStore()
    if not force:
        confirm = typer.confirm("Delete all search history?")
        if not confirm:
            raise typer.Exit(0)
    store.clear()
    console.print("[green]Search history cleared.[/green]")
