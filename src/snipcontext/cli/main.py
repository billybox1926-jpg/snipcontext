"""SnipContext CLI - AI-powered code snippet & context manager."""

import logging
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from snipcontext.config.settings import get_config
from snipcontext.core.models import Language, Snippet, SnippetMetadata
from snipcontext.core.search import HybridSearch
from snipcontext.core.storage import StorageEngine
from snipcontext.providers.base import Provider
from snipcontext.providers.claude import ClaudeProvider
from snipcontext.providers.cursor import CursorProvider
from snipcontext.providers.generic import GenericProvider
from snipcontext.providers.openai import OpenAIProvider

logger = logging.getLogger(__name__)

app = typer.Typer(
    name="snipcontext",
    help="AI-powered code snippet & context manager.",
    add_completion=False,
)
console = Console()


def get_provider(name: str) -> Provider:
    """Return a provider instance by name."""
    providers: dict[str, Provider] = {
        "claude": ClaudeProvider(),
        "cursor": CursorProvider(),
        "openai": OpenAIProvider(),
        "generic": GenericProvider(),
    }
    if name not in providers:
        raise typer.BadParameter(f"Unknown provider: {name}")
    return providers[name]


@app.command()
def add(
    content: str = typer.Argument(..., help="Snippet content"),
    title: Optional[str] = typer.Option(None, "--title", "-t", help="Snippet title"),
    description: Optional[str] = typer.Option(None, "--desc", "-d", help="Snippet description"),
    language: Optional[str] = typer.Option(None, "--lang", "-l", help="Programming language"),
    tags: list[str] = typer.Option([], "--tag", "-T", help="Tag(s) (can be repeated)"),
    from_file: bool = typer.Option(False, "--file", "-f", help="Read content from file"),
    sensitive: bool = typer.Option(
        False, "--sensitive", "-s", help="Mark as sensitive (encrypted)"
    ),
    encrypt: bool = typer.Option(False, "--encrypt", "-e", help="Encrypt content"),
) -> None:
    """Add a new snippet."""
    config = get_config()

    if from_file:
        if content != "":
            console.print(
                "[yellow]Warning: both content and --file given; ignoring content.[/yellow]"
            )
        file_path = Path(content)
        if not file_path.exists():
            console.print(f"[red]File not found: {file_path}[/red]")
            raise typer.Exit(code=1)
        content = file_path.read_text(encoding="utf-8")
        if not title:
            title = file_path.stem

    # Infer language from extension if not provided
    if not language and title:
        suffix = Path(title).suffix.lower()
        lang_map = {
            ".py": "python",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".js": "javascript",
            ".go": "go",
            ".rs": "rust",
            ".sh": "bash",
            ".json": "json",
            ".yaml": "yaml",
            ".yml": "yaml",
        }
        language = lang_map.get(suffix, "unknown")

    # Normalise tags (support comma‑separated values)
    normalized_tags: list[str] = []
    for tag in tags:
        normalized_tags.extend(t.strip() for t in tag.split(",") if t.strip())

    try:
        lang_enum = Language(language) if language else Language.UNKNOWN
    except ValueError:
        lang_enum = Language.UNKNOWN

    # Handle encryption if requested
    if encrypt:
        if not config.encryption.enabled:
            console.print(
                "[red]Encryption is not enabled. Set SNIPCONTEXT_ENCRYPT_ENABLED=true[/red]"
            )
            raise typer.Exit(1)
        storage_obj = StorageEngine(config)
        encrypted = storage_obj.encrypt_content(content)
        snippet = Snippet(
            content="",  # Clear plaintext when encrypted
            encrypted_content=encrypted,
            metadata=SnippetMetadata(
                title=title or "Untitled",
                description=description or "",
                language=lang_enum,
            ),
            tags=normalized_tags,
        )
        console.print(
            f"[green]Added encrypted snippet:[/green] [bold]{snippet.metadata.title}[/bold]"
        )
    else:
        snippet = Snippet(
            content=content,
            metadata=SnippetMetadata(
                title=title or "Untitled",
                description=description or "",
                language=lang_enum,
            ),
            tags=normalized_tags,
        )

    # Auto-tag and dedup suggestions from existing embeddings before persistence.
    if not encrypt:
        auto_tag_enabled = getattr(getattr(config, "auto_tag", None), "enabled", False)
        dedup_enabled = getattr(getattr(config, "dedup", None), "enabled", False)
        if auto_tag_enabled or dedup_enabled:
            search = None
            try:
                from snipcontext.core.auto_tag import AutoTagService
                from snipcontext.core.search import HybridSearch
            except Exception as exc:  # pragma: no cover - defensive for optional path
                logger.debug("Auto-tag/dedup setup skipped: %s", exc)
            else:
                try:
                    search = HybridSearch(config)
                except Exception as exc:  # pragma: no cover
                    logger.debug("Auto-tag/dedup disabled because search setup failed: %s", exc)

            if search is not None:
                storage_engine = StorageEngine(config)
                embedding = None

                # Auto-tag suggestions using the precomputed search/index.
                if auto_tag_enabled:
                    service = AutoTagService(
                        vector_index=search.vector_index,
                        storage=storage_engine,
                        config=config.auto_tag,
                    )
                    try:
                        embedding = search.embedder.encode_query(snippet.to_search_text()).flatten()
                    except Exception as exc:  # pragma: no cover - model/runtime issues
                        logger.debug("Auto-tag embedding failed: %s", exc)
                        embedding = None
                    else:
                        suggested = service.suggest(embedding.tolist())
                        if suggested:
                            merged = sorted({*snippet.tags, *suggested})
                            if config.auto_tag.auto_accept:
                                snippet.tags = merged
                                console.print(
                                    f"[yellow]Suggested tags: {', '.join(merged)}[/yellow]"
                                )
                            else:
                                console.print(
                                    f"[yellow]Suggested tags: {', '.join(merged)}[/yellow]"
                                )
                                choice = (
                                    typer.prompt(
                                        "Accept all, keep existing, or enter tags",
                                        default="a",
                                        show_default=True,
                                    )
                                    .strip()
                                    .lower()
                                )
                                if choice in {"a", "accept", "y", "yes"}:
                                    snippet.tags = merged
                                elif choice in {"e", "existing", "k", "keep"}:
                                    pass  # keep existing tags
                                elif choice:
                                    custom = [
                                        part.strip()
                                        for part in choice.replace(",", " ").split()
                                        if part.strip()
                                    ]
                                    if custom:
                                        snippet.tags = sorted({*snippet.tags, *custom})

                # Dedup check against the single best match.
                if dedup_enabled and embedding is None:
                    try:
                        embedding = search.embedder.encode_query(snippet.to_search_text()).flatten()
                    except Exception as exc:  # pragma: no cover
                        logger.debug("Dedup embedding failed: %s", exc)
                        embedding = None

                if dedup_enabled and embedding is not None:
                    try:
                        if getattr(search.vector_index, "is_trained", False):
                            neighbors = search.vector_index.search(
                                embedding.reshape(1, -1), top_k=1
                            )
                        else:
                            neighbors = []
                    except Exception as exc:  # pragma: no cover
                        logger.debug("Dedup search failed: %s", exc)
                        neighbors = []

                    if neighbors:
                        neighbor_id, score = neighbors[0]
                        if score >= config.dedup.threshold:
                            try:
                                neighbor = storage_engine.get(neighbor_id)
                                neighbor_title = neighbor.metadata.title
                            except Exception:  # pragma: no cover
                                neighbor_title = neighbor_id
                            console.print(
                                f"[yellow]This looks similar to '{neighbor_title}' "
                                f"(score: {score:.2f}). Use --force to add anyway.[/yellow]"
                            )

    if not encrypt:
        storage = StorageEngine(config)
        storage.save(snippet)
        console.print(
            f"[green]Added snippet: {snippet.metadata.title}[/green] [dim]({snippet.id[:6]})[/dim]"
        )


@app.command()
def get(
    snippet_id: str = typer.Argument(..., help="Snippet ID or prefix"),
) -> None:
    """Show a snippet by ID."""
    config = get_config()
    storage = StorageEngine(config)
    snippet = storage.get(snippet_id)
    if not snippet:
        console.print(f"[red]Snippet not found: {snippet_id}[/red]")
        raise typer.Exit(code=1)

    console.print(
        Panel(
            f"[bold]{snippet.metadata.title}[/bold]\n\n{snippet.content}",
            title="Snippet",
            border_style="blue",
        )
    )


@app.command(name="list")
def list_snippets(
    tag: Optional[str] = typer.Option(None, "--tag", "-t", help="Filter by tag"),
    lang: Optional[str] = typer.Option(None, "--lang", "-l", help="Filter by language"),
) -> None:
    """List saved snippets."""
    config = get_config()
    storage = StorageEngine(config)
    snippets = storage.list_all()

    if tag:
        snippets = [s for s in snippets if tag in s.tags]
    if lang:
        snippets = [s for s in snippets if s.metadata.language.value == lang]

    if not snippets:
        console.print("[yellow]No snippets match your filters.[/yellow]")
        return

    table = Table(title="Snippets")
    table.add_column("ID", style="dim")
    table.add_column("Title", style="bold cyan")
    table.add_column("Language")
    table.add_column("Tags")

    for snippet in snippets:
        table.add_row(
            snippet.id[:6],
            snippet.metadata.title,
            snippet.metadata.language.value,
            ", ".join(snippet.tags) if snippet.tags else "",
        )

    console.print(table)


@app.command()
def search(
    query: str = typer.Argument(..., help="Search query"),
    tag: Optional[str] = typer.Option(None, "--tag", "-t", help="Filter by tag"),
    lang: Optional[str] = typer.Option(None, "--lang", "-l", help="Filter by language"),
    limit: int = typer.Option(5, "--limit", "-n", help="Max results"),
) -> None:
    """Search snippets with hybrid BM25 + vector search."""
    config = get_config()
    storage = StorageEngine(config)
    all_snippets = storage.list_all()

    if tag:
        all_snippets = [s for s in all_snippets if tag in s.tags]
    if lang:
        all_snippets = [s for s in all_snippets if s.metadata.language.value == lang]

    if not all_snippets:
        console.print("[yellow]No snippets to search.[/yellow]")
        return

    searcher = HybridSearch(config)
    searcher.index_snippets(all_snippets)
    results = searcher.search(query)

    if not results:
        console.print("[yellow]No results found.[/yellow]")
        return

    console.print(f"[green]Found {len(results)} results:[/green]")
    for idx, result in enumerate(results[:limit], start=1):
        console.print(f"\n[{idx}] {result.snippet.metadata.title} (score: {result.score:.3f})")
        console.print(result.snippet.content)
        console.print(f"Tags: {', '.join(result.snippet.tags)}")


@app.command()
def delete(
    snippet_id: str = typer.Argument(..., help="Snippet ID or prefix"),
    confirm: bool = typer.Option(False, "--yes", help="Skip confirmation"),
) -> None:
    """Delete a snippet."""
    config = get_config()
    storage = StorageEngine(config)
    snippet = storage.get(snippet_id)
    if not snippet:
        console.print(f"[red]Snippet not found: {snippet_id}[/red]")
        raise typer.Exit(code=1)

    if not confirm:
        if not typer.confirm(f"Delete '{snippet.metadata.title}'?"):
            raise typer.Exit(0)

    storage.delete(snippet.id)
    console.print(f"[green]Deleted:[/green] {snippet.metadata.title}")


@app.command()
def stats() -> None:
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


# -- INDEX -----------------------------------------------------------


@app.command()
def index(
    force: bool = typer.Option(False, "--force", help="Skip confirmation prompt"),
) -> None:
    """Rebuild the search index from all stored snippets."""
    from snipcontext.config.settings import get_config
    from snipcontext.core.search import HybridSearch
    from snipcontext.core.storage import StorageEngine

    config = get_config()
    storage = StorageEngine(config)
    snippets = storage.list_all()

    if not snippets:
        console.print("[yellow]No snippets found. Index will be empty.[/yellow]")
        if not force:
            return

    console.print(f"Indexing {len(snippets)} snippets...")
    search = HybridSearch(config)
    search.index_snippets(snippets)
    console.print(f"Index complete. {len(snippets)} snippets indexed.")


# -- PROVIDERS -------------------------------------------------------


@app.command()
def providers() -> None:
    """List available export providers."""
    table = Table(title="Available Providers", show_header=True, header_style="bold magenta")
    table.add_column("Name")
    table.add_column("Description")
    providers_list = [
        ("claude", "Anthropic Claude XML format"),
        ("cursor", "Cursor IDE file-style headers"),
        ("openai", "Delineated sections for ChatGPT/GPT-4"),
        ("generic", "Universal Markdown"),
    ]
    for name, desc in providers_list:
        table.add_row(name, desc)
    console.print(table)


# -- CONFIG ----------------------------------------------------------


config_app = typer.Typer(help="Manage SnipContext configuration.")
app.add_typer(config_app, name="config")


@config_app.command("path")
def config_path() -> None:
    """Show configuration and data directories."""
    config = get_config()
    console.print(f"[bold]Config file:[/bold]  {config.config_file_path}")
    console.print(f"[bold]Data dir:[/bold]     {config.storage.data_dir}")
    console.print(f"[bold]Snippets:[/bold]    {config.snippets_path}")
    console.print(f"[bold]Index:[/bold]       {config.index_path}")


# -- DEMO -----------------------------------------------------------


@app.command()
def demo() -> None:
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
            'package main\n\nimport (\n    "context"\n    "log"\n    "net/http"\n    "os"\n    "os/signal"\n    "syscall"\n    "time"\n)\n\nfunc main() {\n    srv := &http.Server{Addr: ":8080"}\n\n    http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {\n        w.Write([]byte("ok"))\n    })\n\n    go func() {\n        if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {\n            log.Fatalf("listen: %v", err)\n        }\n    }()\n\n    quit := make(chan os.Signal, 1)\n    signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)\n    <-quit\n    log.Println("shutdown...")\n\n    ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)\n    defer cancel()\n    if err := srv.Shutdown(ctx); err != nil {\n        log.Fatalf("server forced to shutdown: %v", err)\n    }\n    log.Println("server exited")\n}',
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
            '#!/usr/bin/env bash\n\nretry() {\n  local max_attempts=5\n  local attempt=0\n  while (( attempt < max_attempts )); do\n    if "$@"; then\n      return 0\n    fi\n    ((attempt++))\n    echo "Attempt $attempt failed. Retrying..." >&2\n    sleep $((attempt * 2))\n  done\n  echo "Command failed after $max_attempts attempts" >&2\n  return 1\n}\n\nretry curl -sSL https://example.com',
        ),
    ]

    console.print("[bold green]Seeding sample snippets...[/bold green]")
    for title, lang, tags, content in samples:
        try:
            lang_enum = Language(lang)
        except ValueError:
            lang_enum = Language.UNKNOWN

        snippet = Snippet(
            content=content,
            metadata=SnippetMetadata(
                title=title,
                language=lang_enum,
            ),
            tags=tags,
        )
        storage.save(snippet)
        console.print(f"  [green]✓[/green] {title}")

    console.print("\n[bold green]Demo snippets ready![/bold green]")
    console.print("Try running:")
    console.print("  [bold]sc search 'retry http'[/bold]")
    console.print("  [bold]sc list --tag python[/bold]")
    console.print("  [bold]sc export claude[/bold]")

    # Optionally show a quick search example
    searcher = HybridSearch(config)
    searcher.index_snippets(storage.list_all())
    results = searcher.search("http retry")
    if results:
        console.print("\n[bold]Example search result:[/bold]")
        top = results[0]
        console.print(f"  {top.snippet.metadata.title} (score: {top.score:.3f})")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    app()
