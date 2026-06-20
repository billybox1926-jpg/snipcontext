"""SnipContext CLI - AI-powered code snippet & context manager."""

from pathlib import Path
from typing import List, Optional

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
    tags: List[str] = typer.Option([], "--tag", "-T", help="Tag(s) (can be repeated)"),
    file: Optional[Path] = typer.Option(None, "--file", "-f", help="Read content from file"),
    sensitive: bool = typer.Option(
        False, "--sensitive", "-s", help="Mark as sensitive (encrypted)"
    ),
    encrypt: bool = typer.Option(False, "--encrypt", "-e", help="Encrypt content"),
) -> None:
    """Add a new snippet."""
    config = get_config()

    if file:
        if content != "":
            console.print(
                "[yellow]Warning: both content and --file given; ignoring content.[/yellow]"
            )
        if not file.exists():
            console.print(f"[red]File not found: {file}[/red]")
            raise typer.Exit(code=1)
        content = file.read_text(encoding="utf-8")
        if not title:
            title = file.stem

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
    normalized_tags: List[str] = []
    for tag in tags:
        normalized_tags.extend(t.strip() for t in tag.split(",") if t.strip())

    try:
        lang_enum = Language(language) if language else Language.UNKNOWN
    except ValueError:
        lang_enum = Language.UNKNOWN

    snippet = Snippet(
        content=content,
        metadata=SnippetMetadata(
            title=title or "Untitled",
            description=description or "",
            language=lang_enum,
        ),
        tags=normalized_tags,
        sensitive=sensitive or encrypt,
    )

    storage = StorageEngine(config)
    stored = storage.save(snippet)

    console.print(
        f"[green]Added snippet: {stored.metadata.title}[/green] [dim]({stored.id[:6]})[/dim]"
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
            snippet.content,
            title=f"{snippet.metadata.title} ({snippet.id})",
            subtitle=f"Language: {snippet.metadata.language.value} | Tags: {snippet.tag_line or '(none)'}",
            border_style="blue",
        )
    )


@app.command()
def list(
    tag: Optional[str] = typer.Option(None, "--tag", "-T", help="Filter by tag"),
    limit: int = typer.Option(50, "--limit", "-n", help="Maximum number to show"),
) -> None:
    """List all snippets."""
    config = get_config()
    storage = StorageEngine(config)
    snippets = storage.list_all()
    if tag:
        snippets = [s for s in snippets if tag in s.tags]

    if not snippets:
        console.print("[yellow]No snippets found.[/yellow]")
        return

    table = Table(title="Snippets", show_header=True, header_style="bold magenta")
    table.add_column("ID", style="dim", width=8)
    table.add_column("Title")
    table.add_column("Language")
    table.add_column("Tags")
    table.add_column("Created")

    for s in snippets[:limit]:
        table.add_row(
            s.id[:6],
            s.metadata.title,
            s.metadata.language.value,
            s.tag_line or "",
            s.created_at.strftime("%Y-%m-%d %H:%M"),
        )
    console.print(table)


@app.command()
def search(
    query: str = typer.Argument(..., help="Search query"),
    mode: str = typer.Option(
        "hybrid", "--mode", "-m", help="Search mode: hybrid, semantic, keyword, tag"
    ),
    provider: Optional[str] = typer.Option(
        None, "--provider", "-p", help="Export provider (claude, cursor, openai, generic)"
    ),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Output file (default: stdout)"
    ),
    top_k: int = typer.Option(10, "--top-k", "-k", help="Number of results"),
) -> None:
    """Search snippets semantically or by keyword/tag."""
    config = get_config()
    storage = StorageEngine(config)
    searcher = HybridSearch(config)

    # If mode is tag, use tag filtering
    if mode == "tag":
        results = [s for s in storage.list_all() if query in s.tags]
        # Convert to SearchResult format for consistent output
        from snipcontext.core.search import SearchResult

        results = [SearchResult(snippet=s, score=1.0) for s in results]
    else:
        searcher.index_snippets(storage.list_all())
        results = searcher.search(query, mode=mode, top_k=top_k)

    if not results:
        console.print("[yellow]No matches found.[/yellow]")
        return

    if provider:
        # Export using provider
        prov = get_provider(provider)
        exported = prov.export([r.snippet for r in results])
        if output:
            output.write_text(exported, encoding="utf-8")
            console.print(f"[green]Exported to {output}[/green]")
        else:
            console.print(exported)
        return

    # Display results
    table = Table(title=f"Search results for '{query}'", show_header=True, header_style="bold cyan")
    table.add_column("Score", style="dim", width=6)
    table.add_column("ID", style="dim", width=8)
    table.add_column("Title")
    table.add_column("Language")

    for r in results[:top_k]:
        table.add_row(
            f"{r.score:.3f}",
            r.snippet.id[:6],
            r.snippet.metadata.title,
            r.snippet.metadata.language.value,
        )
    console.print(table)


@app.command()
def delete(
    snippet_id: str = typer.Argument(..., help="Snippet ID or prefix"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """Delete a snippet."""
    config = get_config()
    storage = StorageEngine(config)
    snippet = storage.get(snippet_id)
    if not snippet:
        console.print(f"[red]Snippet not found: {snippet_id}[/red]")
        raise typer.Exit(code=1)

    if not force:
        confirm = typer.confirm(f"Delete '{snippet.metadata.title}'?")
        if not confirm:
            console.print("[yellow]Aborted.[/yellow]")
            return

    storage.delete(snippet.id)
    console.print(f"[green]Deleted snippet: {snippet.metadata.title}[/green]")


@app.command()
def stats() -> None:
    """Show statistics about the snippet collection."""
    config = get_config()
    storage = StorageEngine(config)
    snippets = storage.list_all()

    if not snippets:
        console.print("[yellow]No snippets found.[/yellow]")
        return

    total = len(snippets)
    langs: dict[str, int] = {}
    tags: dict[str, int] = {}
    for s in snippets:
        lang = s.metadata.language.value
        langs[lang] = langs.get(lang, 0) + 1
        for t in s.tags:
            tags[t] = tags.get(t, 0) + 1

    content = f"Total snippets: {total}\n\n" f"[bold]Languages:[/bold]\n" + "\n".join(
        f"  {lang}: {count}" for lang, count in sorted(langs.items(), key=lambda x: -x[1])
    ) + "\n\n[bold]Tags:[/bold]\n" + "\n".join(
        f"  {tag}: {count}" for tag, count in sorted(tags.items(), key=lambda x: -x[1])[:10]
    )

    console.print(
        Panel(
            content,
            title="SnipContext Stats",
            border_style="green",
        )
    )


@app.command()
def providers() -> None:
    """List available export providers."""
    table = Table(title="Available Providers", show_header=True, header_style="bold magenta")
    table.add_column("Name")
    table.add_column("Description")
    providers_list = [
        ("claude", "Anthropic Claude XML format"),
        ("cursor", "Cursor IDE file‑style headers"),
        ("openai", "Delineated sections for ChatGPT/GPT‑4"),
        ("generic", "Universal Markdown"),
    ]
    for name, desc in providers_list:
        table.add_row(name, desc)
    console.print(table)


@app.command()
def demo() -> None:
    """Run an interactive demo with sample snippets."""
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

    # Quick search example
    searcher = HybridSearch(config)
    searcher.index_snippets(storage.list_all())
    results = searcher.search("http retry")
    if results:
        console.print("\n[bold]Example search result:[/bold]")
        top = results[0]
        console.print(f"  {top.snippet.metadata.title} (score: {top.score:.3f})")


# Entrypoint
if __name__ == "__main__":
    app()
