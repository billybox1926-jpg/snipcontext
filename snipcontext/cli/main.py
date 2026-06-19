"""SnipContext CLI — rich, intuitive command-line interface.

Built with Typer and Rich for beautiful output, tab completion,
and an excellent developer experience.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.logging import RichHandler
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from snipcontext.config.settings import get_config

# Configure logging with Rich
logging.basicConfig(
    level=logging.WARNING,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)],
)
logger = logging.getLogger(__name__)

# Rich console
console = Console()

# Typer app
app = typer.Typer(
    name="snipcontext",
    help="SnipContext — AI-powered code snippet & context manager",
    rich_markup_mode="rich",
    no_args_is_help=True,
    add_completion=True,
)

# Sub-command groups
config_app = typer.Typer(name="config", help="Manage configuration")
app.add_typer(config_app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _print_snippet(snippet, score: Optional[float] = None, idx: Optional[int] = None):
    """Pretty-print a snippet with Rich."""
    from rich.syntax import Syntax

    prefix = f"[{idx}] " if idx else ""
    score_text = f" (score: {score:.3f})" if score else ""

    console.print(f"\n[bold yellow]{prefix}[/bold yellow][bold cyan]{snippet.metadata.title}[/bold cyan][dim]{score_text}[/dim]")

    # Metadata
    if snippet.metadata.description:
        console.print(f"[dim]Description:[/dim] {snippet.metadata.description}")
    console.print(f"[dim]Language:[/dim] {snippet.metadata.language.value}")
    if snippet.tags:
        console.print(f"[dim]Tags:[/dim] {snippet.tag_line}")
    console.print(f"[dim]ID:[/dim] {snippet.id}")
    console.print()

    # Code block
    lang = snippet.metadata.language.value if snippet.metadata.language.value != "unknown" else "text"
    syntax = Syntax(
        snippet.content,
        lang,
        theme="monokai",
        line_numbers=False,
        word_wrap=True,
    )
    console.print(syntax)
    console.print()


def _confirm_action(message: str) -> bool:
    """Ask for confirmation."""
    return typer.confirm(message, default=False)


def _init_config_and_plugins():
    """Initialize config and plugin manager."""
    from snipcontext.plugins.base import PluginManager

    config = get_config()
    pm = PluginManager()
    pm.load_builtin_providers()
    pm.discover()
    return config, pm


def _auto_index_add(config, snippet) -> None:
    """Incrementally add a snippet to the search index (fire-and-forget)."""
    try:
        from snipcontext.core.search import HybridSearch
        searcher = HybridSearch(config)
        if not searcher.load_indices():
            # No existing index yet — build from all snippets
            from snipcontext.core.storage import StorageEngine
            storage = StorageEngine(config)
            snippets = storage.list_all()
            searcher.index_snippets(snippets)
        else:
            searcher.add_snippet(snippet)
    except Exception as exc:
        logger.debug("Auto-index add skipped: %s", exc)


def _auto_index_remove(config, snippet_id: str) -> None:
    """Incrementally remove a snippet from the search index (fire-and-forget)."""
    try:
        from snipcontext.core.search import HybridSearch
        searcher = HybridSearch(config)
        if searcher.load_indices():
            searcher.remove_snippet(snippet_id)
    except Exception as exc:
        logger.debug("Auto-index remove skipped: %s", exc)


def _auto_index_update(config, snippet) -> None:
    """Incrementally update a snippet in the search index (fire-and-forget)."""
    try:
        from snipcontext.core.search import HybridSearch
        searcher = HybridSearch(config)
        if not searcher.load_indices():
            from snipcontext.core.storage import StorageEngine
            storage = StorageEngine(config)
            snippets = storage.list_all()
            searcher.index_snippets(snippets)
        else:
            searcher.update_snippet(snippet)
    except Exception as exc:
        logger.debug("Auto-index update skipped: %s", exc)


# ---------------------------------------------------------------------------
# Main commands
# ---------------------------------------------------------------------------

@app.callback()
def main(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output"),
    debug: bool = typer.Option(False, "--debug", help="Enable debug logging"),
):
    """SnipContext — save, search, and export your best code for LLMs."""
    if debug:
        logging.getLogger().setLevel(logging.DEBUG)
    elif verbose:
        logging.getLogger().setLevel(logging.INFO)


# -- ADD -------------------------------------------------------------

@app.command()
def add(
    content: str = typer.Argument(..., help="Code content or path to file"),
    title: str = typer.Option("", "--title", "-t", help="Snippet title"),
    description: str = typer.Option("", "--desc", "-d", help="Short description"),
    language: str = typer.Option("", "--lang", "-l", help="Programming language"),
    tags: Optional[list[str]] = typer.Option(None, "--tag", help="Tags (repeatable)"),
    from_file: bool = typer.Option(False, "--file", "-f", help="Read content from file path"),
):
    """Add a new code snippet to your collection."""
    from snipcontext.core.models import Language, Snippet, SnippetMetadata
    from snipcontext.core.storage import StorageEngine

    config = get_config()

    tags = tags or []

    # Read content from file if requested
    if from_file:
        path = Path(content)
        if not path.exists():
            console.print(f"[red]File not found: {content}[/red]")
            raise typer.Exit(1)
        content = path.read_text()
        if not title:
            title = path.stem
        if not language:
            ext = path.suffix.lstrip(".").lower()
            ext_lang_map = {
                "py": "python", "js": "javascript", "ts": "typescript",
                "jsx": "jsx", "tsx": "tsx", "html": "html", "css": "css",
                "java": "java", "go": "go", "rs": "rust", "cpp": "cpp",
                "c": "c", "cs": "csharp", "php": "php", "rb": "ruby",
                "swift": "swift", "sql": "sql", "sh": "bash", "yml": "yaml",
                "yaml": "yaml", "json": "json", "toml": "toml", "md": "markdown",
                "dockerfile": "dockerfile", "tf": "terraform",
            }
            language = ext_lang_map.get(ext, "")

    # Auto-title from first line if not provided
    if not title:
        first_line = content.strip().split("\n")[0][:50]
        title = first_line or "Untitled Snippet"

    # Build snippet
    try:
        lang_enum = Language(language) if language else Language.UNKNOWN
    except ValueError:
        lang_enum = Language.UNKNOWN

    snippet = Snippet(
        content=content,
        metadata=SnippetMetadata(
            title=title,
            description=description,
            language=lang_enum,
        ),
        tags=tags,
    )

    storage = StorageEngine(config)
    storage.save(snippet)

    # Auto-index: incrementally add to search index
    _auto_index_add(config, snippet)

    console.print(f"[green]Added snippet:[/green] [bold]{snippet.metadata.title}[/bold]")
    console.print(f"   [dim]ID: {snippet.id}[/dim]")
    console.print(f"   [dim]Tags: {snippet.tag_line or '(none)'}[/dim]")


# -- GET -------------------------------------------------------------

@app.command()
def get(
    snippet_id: str = typer.Argument(..., help="Snippet ID or prefix"),
    raw: bool = typer.Option(False, "--raw", "-r", help="Print only code, no metadata"),
):
    """Retrieve a snippet by ID."""
    from snipcontext.core.storage import StorageEngine, SnippetNotFoundError

    config = get_config()
    storage = StorageEngine(config)

    # Try exact match first, then prefix match
    try:
        snippet = storage.get(snippet_id)
    except SnippetNotFoundError:
        matches = [s for s in storage.iter_all() if s.id.startswith(snippet_id)]
        if len(matches) == 1:
            snippet = matches[0]
        elif len(matches) > 1:
            console.print(f"[yellow]Multiple matches for prefix '{snippet_id}':[/yellow]")
            for s in matches:
                console.print(f"  [dim]{s.id}[/dim] — {s.metadata.title}")
            raise typer.Exit(1)
        else:
            console.print(f"[red]Snippet not found: {snippet_id}[/red]")
            raise typer.Exit(1)

    snippet.record_access()
    storage.save(snippet)

    if raw:
        console.print(snippet.content)
    else:
        _print_snippet(snippet)


# -- SEARCH ----------------------------------------------------------

@app.command()
def search(
    query: str = typer.Argument(..., help="Search query"),
    mode: str = typer.Option("hybrid", "--mode", "-m", help="Search mode: semantic, keyword, hybrid, tag"),
    top_k: int = typer.Option(10, "--limit", "-n", help="Max results"),
    index: bool = typer.Option(False, "--index", "-i", help="Force reindex before search"),
):
    """Search snippets with semantic + keyword hybrid search."""
    from snipcontext.core.search import HybridSearch
    from snipcontext.core.storage import StorageEngine

    config = get_config()
    storage = StorageEngine(config)
    searcher = HybridSearch(config)

    # Build or load index
    if index or not searcher.load_indices():
        console.print("[yellow]Building search index...[/yellow]")
        snippets = storage.list_all()
        if not snippets:
            console.print("[yellow]No snippets to index. Add some first with `sc add`.[/yellow]")
            raise typer.Exit(0)
        searcher.index_snippets(snippets)
        console.print(f"[green]Indexed {len(snippets)} snippets[/green]")

    results = searcher.search(query, top_k=top_k, mode=mode)

    if not results:
        console.print(f"[yellow]No results for '{query}'[/yellow]")
        raise typer.Exit(0)

    console.print(f"\n[bold]{len(results)} results[/bold] for '[cyan]{query}[/cyan]' ([dim]{mode}[/dim]):\n")
    for i, result in enumerate(results, 1):
        _print_snippet(result.snippet, score=result.score, idx=i)
        console.print()


# -- LIST ------------------------------------------------------------

@app.command("list")
def list_snippets(
    tag: Optional[str] = typer.Option(None, "--tag", "-t", help="Filter by tag"),
    language: Optional[str] = typer.Option(None, "--lang", "-l", help="Filter by language"),
    sort: str = typer.Option("updated", "--sort", "-s", help="Sort by: updated, created, title, access"),
):
    """List all snippets with optional filters."""
    from snipcontext.core.storage import StorageEngine

    config = get_config()
    storage = StorageEngine(config)

    snippets = storage.list_all()

    # Apply filters
    if tag:
        tag = tag.strip().lstrip("#").lower()
        snippets = [s for s in snippets if tag in s.tags]
    if language:
        snippets = [s for s in snippets if s.metadata.language.value == language.lower()]

    # Sort
    sort_key = {
        "updated": lambda s: s.updated_at,
        "created": lambda s: s.created_at,
        "title": lambda s: s.metadata.title.lower(),
        "access": lambda s: s.access_count,
    }.get(sort, lambda s: s.updated_at)
    snippets.sort(key=sort_key, reverse=(sort in ("updated", "created", "access")))

    if not snippets:
        console.print("[yellow]No snippets found.[/yellow]")
        return

    table = Table(
        title=f"Snippets ({len(snippets)} total)",
        show_header=True,
        header_style="bold magenta",
        row_styles=["", "dim"],
    )
    table.add_column("ID", style="dim", no_wrap=True, width=8)
    table.add_column("Title", style="cyan", no_wrap=False)
    table.add_column("Language", style="green", width=12)
    table.add_column("Tags", style="yellow", width=20)
    table.add_column("Updated", style="dim", width=10)

    from datetime import datetime
    for s in snippets:
        updated = s.updated_at.strftime("%Y-%m-%d") if isinstance(s.updated_at, datetime) else "?"
        table.add_row(
            s.id[:6],
            s.metadata.title,
            s.metadata.language.value,
            ", ".join(s.tags[:3]) + ("..." if len(s.tags) > 3 else ""),
            updated,
        )

    console.print(table)


# -- EDIT ------------------------------------------------------------

@app.command()
def edit(
    snippet_id: str = typer.Argument(..., help="Snippet ID or prefix"),
    content: Optional[str] = typer.Option(None, "--content", "-c", help="New code content"),
    title: Optional[str] = typer.Option(None, "--title", "-t", help="New title"),
    description: Optional[str] = typer.Option(None, "--desc", "-d", help="New description"),
    add_tags: Optional[list[str]] = typer.Option(None, "--add-tag", help="Add tags"),
    remove_tags: Optional[list[str]] = typer.Option(None, "--remove-tag", help="Remove tags"),
    message: str = typer.Option("", "--message", "-m", help="Version bump message"),
):
    """Edit an existing snippet."""
    from snipcontext.core.storage import StorageEngine, SnippetNotFoundError

    config = get_config()
    storage = StorageEngine(config)

    add_tags = add_tags or []
    remove_tags = remove_tags or []

    try:
        snippet = storage.get(snippet_id)
    except SnippetNotFoundError:
        console.print(f"[red]Snippet not found: {snippet_id}[/red]")
        raise typer.Exit(1)

    # Version bump before changes
    snippet.bump_version(message or f"Edit: {title or 'metadata update'}")

    # Apply changes
    if content:
        snippet.content = content
    if title:
        snippet.metadata.title = title
    if description:
        snippet.metadata.description = description
    for t in add_tags:
        snippet.merge_tags([t])
    for t in remove_tags:
        t = t.strip().lstrip("#").lower()
        if t in snippet.tags:
            snippet.tags.remove(t)
            snippet.tags.sort()

    snippet.touch()
    storage.save(snippet)

    # Auto-index: update search index incrementally
    _auto_index_update(config, snippet)

    console.print(f"[green]Updated:[/green] {snippet.metadata.title} [dim]({snippet_id})[/dim]")


# -- DELETE ----------------------------------------------------------

@app.command()
def delete(
    snippet_id: str = typer.Argument(..., help="Snippet ID or prefix"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
):
    """Delete a snippet."""
    from snipcontext.core.storage import StorageEngine, SnippetNotFoundError

    config = get_config()
    storage = StorageEngine(config)

    try:
        snippet = storage.get(snippet_id)
    except SnippetNotFoundError:
        console.print(f"[red]Snippet not found: {snippet_id}[/red]")
        raise typer.Exit(1)

    if not force and not _confirm_action(f"Delete '{snippet.metadata.title}'?"):
        console.print("Cancelled.")
        return

    storage.delete(snippet.id)

    # Auto-index: remove from search index incrementally
    _auto_index_remove(config, snippet.id)

    console.print(f"[red]Deleted:[/red] {snippet.metadata.title}")


# -- EXPORT ----------------------------------------------------------

@app.command()
def export(
    query: Optional[str] = typer.Option(None, "--query", "-q", help="Export search results"),
    ids: Optional[list[str]] = typer.Option(None, "--id", help="Export specific snippet IDs"),
    provider: str = typer.Option("generic", "--provider", "-p", help="Export format provider"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file (default: stdout)"),
    top_k: int = typer.Option(10, "--limit", "-n", help="Max results for query export"),
):
    """Export snippets in LLM-optimized format."""
    from snipcontext.core.search import HybridSearch
    from snipcontext.core.storage import StorageEngine
    from snipcontext.plugins.base import PluginManager

    config = get_config()
    storage = StorageEngine(config)

    ids = ids or []

    pm = PluginManager()
    pm.load_builtin_providers()

    try:
        prov = pm.get_provider(provider)
    except KeyError:
        console.print(f"[red]Unknown provider: {provider}[/red]")
        console.print(f"Available: {', '.join(pm.list_providers().keys())}")
        raise typer.Exit(1)

    # Collect snippets
    snippets: list = []

    if ids:
        for sid in ids:
            try:
                snippets.append(storage.get(sid))
            except Exception:
                console.print(f"[yellow]Warning: snippet not found: {sid}[/yellow]")
    elif query:
        searcher = HybridSearch(config)
        if not searcher.load_indices():
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


# -- INDEX -----------------------------------------------------------

@app.command()
def build_index(
    force: bool = typer.Option(False, "--force", "-f", help="Force rebuild even if index exists"),
    watch: bool = typer.Option(False, "--watch", "-w", help="Watch snippet directory for changes and reindex in real-time"),
):
    """Build or rebuild the semantic search index."""
    from snipcontext.core.search import HybridSearch
    from snipcontext.core.storage import StorageEngine

    config = get_config()
    storage = StorageEngine(config)
    searcher = HybridSearch(config)

    snippets = storage.list_all()
    if not snippets:
        console.print("[yellow]No snippets found. Add some first![/yellow]")
        return

    if not force and searcher.load_indices():
        console.print(f"[yellow]Index already exists ({len(snippets)} snippets). Use --force to rebuild.[/yellow]")
        return

    console.print(f"[dim]Building index for {len(snippets)} snippets...[/dim]")
    searcher.index_snippets(snippets)
    console.print(f"[green]Index built: {len(snippets)} snippets indexed[/green]")

    if watch:
        _watch_and_reindex(config, storage, searcher)


def _watch_and_reindex(config, storage, searcher) -> None:
    """Watch the snippet directory for filesystem changes and reindex.

    Uses inotifywait if available, otherwise falls back to polling.
    On Termux/Android, polling is the reliable fallback.
    """
    import subprocess
    import time

    snippets_dir = str(config.snippets_path)
    console.print(f"[dim]Watching {snippets_dir} for changes... (Ctrl+C to stop)[/dim]")

    # Try inotifywait first
    use_inotify = False
    try:
        subprocess.run(["which", "inotifywait"], capture_output=True, check=True, timeout=5)
        use_inotify = True
    except Exception:
        pass

    if use_inotify:
        console.print("[dim]Using inotifywait for real-time monitoring[/dim]")
        try:
            proc = subprocess.Popen(
                ["inotifywait", "-m", "-r", "-e", "create,delete,modify,move",
                 "--format", "%e %f", snippets_dir],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            last_reindex = 0.0
            for line in proc.stdout:
                line = line.strip()
                if not line:
                    continue
                now = time.time()
                # Debounce: wait 1s after last event before reindexing
                if now - last_reindex < 1.0:
                    continue
                last_reindex = now
                console.print(f"[dim]Change detected: {line}[/dim]")
                try:
                    snippets = storage.list_all()
                    if snippets:
                        searcher.index_snippets(snippets)
                        console.print(f"[green]Reindexed {len(snippets)} snippets[/green]")
                except Exception as exc:
                    console.print(f"[yellow]Reindex failed: {exc}[/yellow]")
        except KeyboardInterrupt:
            proc.terminate()
            console.print("\n[dim]Watch stopped.[/dim]")
    else:
        # Polling fallback (works everywhere, including Termux)
        console.print("[dim]inotifywait not available — using polling (2s interval)[/dim]")
        last_mtime = _dir_max_mtime(config.snippets_path)
        try:
            while True:
                time.sleep(2)
                current_mtime = _dir_max_mtime(config.snippets_path)
                if current_mtime != last_mtime:
                    last_mtime = current_mtime
                    console.print("[dim]Change detected, reindexing...[/dim]")
                    try:
                        snippets = storage.list_all()
                        if snippets:
                            searcher.index_snippets(snippets)
                            console.print(f"[green]Reindexed {len(snippets)} snippets[/green]")
                    except Exception as exc:
                        console.print(f"[yellow]Reindex failed: {exc}[/yellow]")
        except KeyboardInterrupt:
            console.print("\n[dim]Watch stopped.[/dim]")


def _dir_max_mtime(path) -> float:
    """Return the max mtime of all files in a directory (recursive)."""
    import os
    max_mtime = 0.0
    try:
        for root, dirs, files in os.walk(str(path)):
            for f in files:
                fp = os.path.join(root, f)
                try:
                    m = os.path.getmtime(fp)
                    if m > max_mtime:
                        max_mtime = m
                except OSError:
                    pass
    except OSError:
        pass
    return max_mtime


# -- STATS -----------------------------------------------------------

@app.command()
def stats():
    """Show collection statistics."""
    from snipcontext.core.storage import StorageEngine

    config = get_config()
    storage = StorageEngine(config)

    s = storage.get_stats()
    total = s["total_snippets"]

    if total == 0:
        console.print("[yellow]No snippets in your collection yet.[/yellow]")
        console.print("Add one with: [bold]sc add 'your code here' --title 'My Snippet'[/bold]")
        return

    console.print(Panel(
        f"""
[bold]Collection Overview[/bold]
  Snippets: {total}
  Unique Tags: {s['total_tags']}
  Languages: {len(s['languages'])}

[bold]By Language:[/bold]
{chr(10).join(f"  {lang}: {count}" for lang, count in s['languages'].items())}

[bold]Storage:[/bold]
  Data directory: {config.storage.data_dir}
  Snippets: {config.snippets_path}
  Index: {config.index_path}
        """.strip(),
        title="SnipContext Stats",
        border_style="green",
    ))


# -- PROVIDERS -------------------------------------------------------

@app.command()
def providers():
    """List available export providers."""
    from snipcontext.plugins.base import PluginManager

    pm = PluginManager()
    pm.load_builtin_providers()

    table = Table(title="Export Providers", show_header=True)
    table.add_column("Name", style="cyan")
    table.add_column("Description", style="white")
    table.add_column("Format", style="green")

    for name, desc in pm.list_providers().items():
        fmt = pm._providers.get(name)
        fmt_name = fmt.format if fmt and hasattr(fmt, 'format') else "?"
        table.add_row(name, desc, str(fmt_name))

    console.print(table)


# ---------------------------------------------------------------------------
# Config sub-commands
# ---------------------------------------------------------------------------

@config_app.command("show")
def config_show():
    """Show current configuration."""
    config = get_config()
    import yaml

    payload = config.model_dump(mode="json")
    console.print(Panel(
        yaml.safe_dump(payload, default_flow_style=False, sort_keys=False),
        title="Configuration",
        border_style="blue",
    ))
    console.print(f"\n[dim]Config file: {config.config_file_path}[/dim]")


@config_app.command("init")
def config_init(
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing config"),
):
    """Initialize configuration file with defaults."""
    config = get_config()
    if config.config_file_path.exists() and not force:
        console.print(f"[yellow]Config already exists at {config.config_file_path}[/yellow]")
        console.print("Use --force to overwrite.")
        return

    config.save_to_file()
    console.print(f"[green]Configuration written to:[/green] {config.config_file_path}")


@config_app.command("path")
def config_path():
    """Show configuration and data directories."""
    config = get_config()
    console.print(f"[bold]Config file:[/bold]  {config.config_file_path}")
    console.print(f"[bold]Data dir:[/bold]     {config.storage.data_dir}")
    console.print(f"[bold]Snippets:[/bold]    {config.snippets_path}")
    console.print(f"[bold]Index:[/bold]       {config.index_path}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def _main():
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    _main()
