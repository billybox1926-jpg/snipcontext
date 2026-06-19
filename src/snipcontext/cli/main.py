"""SnipContext CLI — rich, intuitive command-line interface.

Built with Typer and Rich for beautiful output, tab completion,
and an excellent developer experience.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.logging import RichHandler
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from snipcontext.config.settings import get_config

# Module-level Option constants to avoid B008
_OPT_TAG = typer.Option(None, "--tag", "-t", help="Filter by tag")
_OPT_LANG = typer.Option(None, "--lang", "-l", help="Filter by language")
_OPT_TAGS = typer.Option([], "--tag", help="Tags (repeatable)")
_OPT_CONTENT = typer.Option(None, "--content", "-c", help="New code content")
_OPT_TITLE = typer.Option(None, "--title", "-t", help="New title")
_OPT_DESC = typer.Option(None, "--desc", "-d", help="New description")
_OPT_ADD_TAGS = typer.Option([], "--add-tag", help="Add tags")
_OPT_REMOVE_TAGS = typer.Option([], "--remove-tag", help="Remove tags")
_OPT_QUERY = typer.Option(None, "--query", "-q", help="Export search results")
_OPT_IDS = typer.Option([], "--id", help="Export specific snippet IDs")
_OPT_OUTPUT = typer.Option(None, "--output", "-o", help="Output file (default: stdout)")

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


def _print_snippet(snippet, score: float | None = None, idx: int | None = None):
    """Pretty-print a snippet with Rich."""
    from rich.syntax import Syntax

    prefix = f"[{idx}] " if idx else ""
    score_text = f" (score: {score:.3f})" if score else ""

    console.print(
        f"\n[bold yellow]{prefix}[/bold yellow][bold cyan]{snippet.metadata.title}[/bold cyan][dim]{score_text}[/dim]"
    )

    # Metadata
    if snippet.metadata.description:
        console.print(f"[dim]Description:[/dim] {snippet.metadata.description}")
    console.print(f"[dim]Language:[/dim] {snippet.metadata.language.value}")
    if snippet.tags:
        console.print(f"[dim]Tags:[/dim] {snippet.tag_line}")
    console.print(f"[dim]ID:[/dim] {snippet.id}")
    console.print()

    # Code block
    lang = (
        snippet.metadata.language.value if snippet.metadata.language.value != "unknown" else "text"
    )
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
    content: str | None = typer.Argument(
        None, help="Code content or path to file (reads from stdin if omitted)"
    ),
    title: str = typer.Option("", "--title", "-t", help="Snippet title"),
    description: str = typer.Option("", "--desc", "-d", help="Short description"),
    language: str = typer.Option("", "--lang", "-l", help="Programming language"),
    tags: list[str] = _OPT_TAGS,
    from_file: bool = typer.Option(False, "--file", "-f", help="Read content from file path"),
):
    """Add a new code snippet to your collection."""
    from snipcontext.core.models import Language, Snippet, SnippetMetadata
    from snipcontext.core.storage import StorageEngine

    config = get_config()

    # Read content from stdin if not provided and stdin has data
    if content is None:
        if not sys.stdin.isatty():
            content = sys.stdin.read()
        else:
            console.print(
                "[red]Error: No content provided. Pass content as argument, use --file, or pipe content via stdin.[/red]"
            )
            raise typer.Exit(1)

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
                "py": "python",
                "js": "javascript",
                "ts": "typescript",
                "jsx": "jsx",
                "tsx": "tsx",
                "html": "html",
                "css": "css",
                "java": "java",
                "go": "go",
                "rs": "rust",
                "cpp": "cpp",
                "c": "c",
                "cs": "csharp",
                "php": "php",
                "rb": "ruby",
                "swift": "swift",
                "sql": "sql",
                "sh": "bash",
                "yml": "yaml",
                "yaml": "yaml",
                "json": "json",
                "toml": "toml",
                "md": "markdown",
                "dockerfile": "dockerfile",
                "tf": "terraform",
            }
            language = ext_lang_map.get(ext, "")

    # Auto-title from first line if not provided
    if not title:
        first_line = content.strip().split("\n")[0][:50]
        title = first_line or "Untitled Snippet"

    # Validate content is not empty
    if not content.strip():
        console.print("[red]Error: Content cannot be empty.[/red]")
        raise typer.Exit(1)

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
    from snipcontext.core.storage import SnippetNotFoundError, StorageEngine

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
            raise typer.Exit(1) from SnippetNotFoundError()
        else:
            console.print(f"[red]Snippet not found: {snippet_id}[/red]")
            raise typer.Exit(1) from SnippetNotFoundError()

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
    mode: str = typer.Option(
        "hybrid", "--mode", "-m", help="Search mode: semantic, keyword, hybrid, tag"
    ),
    top_k: int = typer.Option(10, "--limit", "-n", help="Max results"),
    index: bool = typer.Option(False, "--index", "-i", help="Force reindex before search"),
    threshold: float = typer.Option(
        None, "--threshold", "-t", help="Minimum relevance score (0.0-1.0)"
    ),
    fuzzy: bool = typer.Option(
        False, "--fuzzy", "-f", help="Enable fuzzy matching for keyword search"
    ),
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

    results = searcher.search(
        query,
        top_k=top_k,
        mode=mode,
        min_score=threshold,
        fuzzy=fuzzy,
    )

    if not results:
        console.print(f"[yellow]No results for '{query}'[/yellow]")
        # Suggest alternatives
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


# -- LIST ------------------------------------------------------------


@app.command("list")
def list_snippets(
    tag: str | None = _OPT_TAG,
    language: str | None = _OPT_LANG,
    sort: str = typer.Option(
        "updated", "--sort", "-s", help="Sort by: updated, created, title, access"
    ),
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
    content: str | None = _OPT_CONTENT,
    title: str | None = _OPT_TITLE,
    description: str | None = _OPT_DESC,
    add_tags: list[str] = _OPT_ADD_TAGS,
    remove_tags: list[str] = _OPT_REMOVE_TAGS,
    message: str = typer.Option("", "--message", "-m", help="Version bump message"),
):
    """Edit an existing snippet."""
    from snipcontext.core.storage import SnippetNotFoundError, StorageEngine

    config = get_config()
    storage = StorageEngine(config)

    try:
        snippet = storage.get(snippet_id)
    except SnippetNotFoundError as err:
        console.print(f"[red]Snippet not found: {snippet_id}[/red]")
        raise typer.Exit(1) from err

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

    console.print(f"[green]Updated:[/green] {snippet.metadata.title} [dim]({snippet_id})[/dim]")


# -- DELETE ----------------------------------------------------------


@app.command()
def delete(
    snippet_id: str = typer.Argument(..., help="Snippet ID or prefix"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
):
    """Delete a snippet."""
    from snipcontext.core.storage import SnippetNotFoundError, StorageEngine

    config = get_config()
    storage = StorageEngine(config)

    try:
        snippet = storage.get(snippet_id)
    except SnippetNotFoundError as err:
        console.print(f"[red]Snippet not found: {snippet_id}[/red]")
        raise typer.Exit(1) from err

    if not force and not _confirm_action(f"Delete '{snippet.metadata.title}'?"):
        console.print("Cancelled.")
        return

    storage.delete(snippet.id)
    console.print(f"[red]Deleted:[/red] {snippet.metadata.title}")


# -- EXPORT ----------------------------------------------------------

# Module-level Option constants to avoid B008
_OPT_QUERY = typer.Option(None, "--query", "-q", help="Export search results")
_OPT_IDS = typer.Option([], "--id", help="Export specific snippet IDs")
_OPT_PROVIDER = typer.Option("generic", "--provider", "-p", help="Export format provider")
_OPT_OUTPUT = typer.Option(None, "--output", "-o", help="Output file (default: stdout)")
_OPT_TOP_K = typer.Option(10, "--limit", "-n", help="Max results for query export")


@app.command()
def export(
    query: str | None = _OPT_QUERY,
    ids: list[str] = _OPT_IDS,
    provider: str = _OPT_PROVIDER,
    output: str | None = _OPT_OUTPUT,
    top_k: int = _OPT_TOP_K,
):
    """Export snippets in LLM-optimized format."""
    from snipcontext.core.search import HybridSearch
    from snipcontext.core.storage import StorageEngine
    from snipcontext.plugins.base import PluginManager

    config = get_config()
    storage = StorageEngine(config)

    pm = PluginManager()
    pm.load_builtin_providers()

    try:
        prov = pm.get_provider(provider)
    except KeyError as err:
        console.print(f"[red]Unknown provider: {provider}[/red]")
        console.print(f"Available: {', '.join(pm.list_providers().keys())}")
        raise typer.Exit(1) from err

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
        console.print(
            f"[yellow]Index already exists ({len(snippets)} snippets). Use --force to rebuild.[/yellow]"
        )
        return

    console.print(f"[dim]Building index for {len(snippets)} snippets...[/dim]")
    searcher.index_snippets(snippets)
    console.print(f"[green]Index built: {len(snippets)} snippets indexed[/green]")


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

    console.print(
        Panel(
            f"""
[bold]Collection Overview[/bold]
  Snippets: {total}
  Unique Tags: {s["total_tags"]}
  Languages: {len(s["languages"])}

[bold]By Language:[/bold]
{chr(10).join(f"  {lang}: {count}" for lang, count in s["languages"].items())}

[bold]Storage:[/bold]
  Data directory: {config.storage.data_dir}
  Snippets: {config.snippets_path}
  Index: {config.index_path}
        """.strip(),
            title="SnipContext Stats",
            border_style="green",
        )
    )


# -- DEMO -----------------------------------------------------------


@app.command()
def demo():
    """Run an interactive demo with sample snippets."""
    from snipcontext.core.models import Language, Snippet, SnippetMetadata
    from snipcontext.core.search import HybridSearch
    from snipcontext.core.storage import StorageEngine

    config = get_config()
    storage = StorageEngine(config)

    # Do not overwrite existing data silently
    existing = storage.list_all()
    if existing:
        console.print("[yellow]Demo mode: existing snippets detected.[/yellow]")
        console.print(
            "Run [bold]sc list[/bold] to see them, or clear your snippets dir to start fresh."
        )
        return

    samples = [
        (
            "FastAPI dependency injection example",
            "python",
            ["fastapi", "di", "web"],
            'from fastapi import Depends, FastAPI\n\napp = FastAPI()\n\ndef get_db():\n    db = {"key": "value"}\n    try:\n        yield db\n    finally:\n        db.close()\n\n@app.get("/")\ndef read_root(db: dict = Depends(get_db)):\n    return {"message": "Hello", "db": db}',
        ),
        (
            "React useEffect data fetch hook",
            "typescript",
            ["react", "hooks", "fetch"],
            'import { useEffect, useState } from "react";\n\ntype Post = { id: number; title: string };\n\nexport function usePosts(url: string) {\n  const [posts, setPosts] = useState<Post[]>([]);\n  const [loading, setLoading] = useState(true);\n\n  useEffect(() => {\n    let cancelled = false;\n    setLoading(true);\n\n    fetch(url)\n      .then((res) => res.json())\n      .then((data) => {\n        if (!cancelled) {\n          setPosts(data);\n          setLoading(false);\n        }\n      });\n\n    return () => {\n      cancelled = true;\n    };\n  }, [url]);\n\n  return { posts, loading };\n}',
        ),
        (
            "Python requests with retry",
            "python",
            ["requests", "retry", "http"],
            'import requests\nfrom requests.adapters import HTTPAdapter\nfrom urllib3.util.retry import Retry\n\ndef requests_session():\n    session = requests.Session()\n    retries = Retry(\n        total=4,\n        backoff_factor=0.5,\n        status_forcelist=[500, 502, 503, 504],\n    )\n    session.mount("https://", HTTPAdapter(max_retries=retries))\n    return session\n\nif __name__ == "__main__":\n    s = requests_session()\n    print(s.get("https://httpbin.org/get").status_code)',
        ),
        (
            "SQLAlchemy async session factory",
            "python",
            ["sqlalchemy", "async", "database"],
            'from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine\nfrom sqlalchemy.orm import sessionmaker\n\nDATABASE_URL = "sqlite+aiosqlite:///./app.db"\n\nengine = create_async_engine(DATABASE_URL, echo=False, future=True)\nAsyncSessionLocal = sessionmaker(\n    bind=engine,\n    class_=AsyncSession,\n    expire_on_commit=False,\n)\n\nasync def get_session() -> AsyncSession:\n    async with AsyncSessionLocal() as session:\n        yield session',
        ),
        (
            "Go graceful shutdown HTTP server",
            "go",
            ["go", "http", "server"],
            'package main\n\nimport (\n    "context"\n    "log"\n    "net/http"\n    "os"\n    "os/signal"\n    "syscall"\n    "time"\n)\n\nfunc main() {\n    srv := &http.Server{Addr: ":8080"}\n\n    http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {\n        w.Write([]byte("ok"))\n    })\n\n    go func() {\n        if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {\n            log.Fatalf("listen: %v", err)\n        }\n    }()\n\n    quit := make(chan os.Signal, 1)\n    signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)\n    <-quit\n    log.Println("shutdown...")\n    ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)\n    defer cancel()\n    if err := srv.Shutdown(ctx); err != nil {\n        log.Fatalf("server forced to shutdown: %v", err)\n    }\n    log.Println("server exited")\n}',
        ),
        (
            "TypeScript zod schema for user input",
            "typescript",
            ["zod", "validation", "typescript"],
            'import { z } from "zod";\n\nexport const UserSchema = z.object({\n  id: z.string().uuid(),\n  email: z.string().email(),\n  role: z.enum(["admin", "member", "viewer"]).default("viewer"),\n  metadata: z.record(z.string()).optional(),\n});\n\nexport type User = z.infer<typeof UserSchema>;\n\nconst parsed = UserSchema.parse(input);',
        ),
        (
            "Rust error handling with anyhow",
            "rust",
            ["rust", "error-handling"],
            'use anyhow::{Context, Result};\n\nfn run() -> Result<()> {\n    let path = std::env::var("CONFIG_PATH")\n        .context("CONFIG_PATH must be set")?;\n\n    let text = std::fs::read_to_string(&path)\n        .with_context(|| format!("failed to read {path}"))?;\n\n    println!("{text}");\n    Ok(())\n}\n\nfn main() {\n    if let Err(err) = run() {\n        eprintln!("error: {err:#}");\n    }\n}',
        ),
        (
            "Bash retry wrapper for flaky commands",
            "bash",
            ["bash", "retry", "shell"],
            '#!/usr/bin/env bash\nset -euo pipefail\n\nretry() {\n  local max=${1:-3}\n  local delay=${2:-1}\n  local attempt=1\n  until "$@"; do\n    if (( attempt >= max )); then\n      echo "failed after ${attempt} attempts" >&2\n      return 1\n    fi\n    echo "attempt ${attempt} failed, retrying in ${delay}s..." >&2\n    sleep "${delay}"\n    ((attempt++))\n  done\n}\n\nretry 5 2 curl -fsS https://httpbin.org/get',
        ),
    ]

    snippets = []
    for title, language, tags, content in samples:
        try:
            lang_enum = Language(language)
        except ValueError:
            lang_enum = Language.UNKNOWN
        snippets.append(
            Snippet(
                content=content,
                metadata=SnippetMetadata(title=title, language=lang_enum),
                tags=tags,
            )
        )

    saved = []
    for snippet in snippets:
        storage.save(snippet)
        saved.append(snippet)

    console.print(f"[green]Seeded {len(saved)} demo snippets.[/green]")

    console.print("\n[bold]Listing snippets:[/bold]")
    for s in saved:
        console.print(f"  - [cyan]{s.metadata.title}[/cyan] [dim]({s.id[:6]})[/dim]")

    console.print("\n[bold]Sample search (semantic):[/bold]")
    try:
        from snipcontext.core.search import HybridSearch

        searcher = HybridSearch(config)
        if searcher.load_indices():
            query = "async python"
            results = searcher.search(query, top_k=3)
            if results:
                console.print(f"[dim]Query:[/dim] [bold]'{query}'[/bold]")
                for idx, result in enumerate(results, 1):
                    _print_snippet(result.snippet, score=result.score, idx=idx)
            else:
                console.print("[yellow]Search returned no results.[/yellow]")
        else:
            console.print(
                "[yellow]No search index available. Run [bold]sc build-index[/bold] after adding snippets.[/yellow]"
            )
    except Exception as exc:  # pragma: no cover - best-effort demo path
        console.print(f"[yellow]Demo search skipped: {exc}[/yellow]")

    console.print("\n[bold]Sample export (generic):[/bold]")
    try:
        from snipcontext.plugins.base import PluginManager

        pm = PluginManager()
        pm.load_builtin_providers()
        provider = pm.get_provider("generic")
        console.print(Markdown(provider.export_batch(saved)))
    except Exception as exc:  # pragma: no cover - best-effort demo path
        console.print(f"[yellow]Demo export skipped: {exc}[/yellow]")

    console.print("\n[bold cyan]Next steps:[/bold cyan]")
    console.print("  - [bold]sc list[/bold]              Review seeded snippets")
    console.print("  - [bold]sc search DI in Python[/bold]  Try semantic search")
    console.print("  - [bold]sc add[/bold] 'your code'...  Add your own")
    console.print("  - [bold]sc build-index[/bold]           Enable semantic search")


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
        fmt_name = fmt.format if fmt and hasattr(fmt, "format") else "?"
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
    console.print(
        Panel(
            yaml.safe_dump(payload, default_flow_style=False, sort_keys=False),
            title="Configuration",
            border_style="blue",
        )
    )
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
