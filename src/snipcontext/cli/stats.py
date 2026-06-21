"""Stats and demo CLI commands."""

import logging

import typer
from rich.console import Console
from rich.panel import Panel

from snipcontext.cli.context import get_context as _get_context

logger = logging.getLogger(__name__)
console = Console()


def register_commands(app: typer.Typer) -> None:
    """Register stats and demo commands on the given Typer app."""

    @app.command()  # type: ignore[untyped-decorator]
    def stats() -> None:
        """Show collection statistics."""
        config, storage, _ = _get_context()
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

    @app.command()  # type: ignore[untyped-decorator]
    def demo() -> None:
        """Run an interactive demo with sample snippets."""
        from snipcontext.core.models import Language, Snippet, SnippetMetadata
        from snipcontext.core.search import HybridSearch
        from snipcontext.core.storage import StorageEngine

        config = _get_context()[0]
        storage = StorageEngine(config)

        existing = storage.list_all()
        if existing:
            console.print("[yellow]Demo mode: existing snippets detected.[/yellow]")
            console.print("Run [bold]sc list[/bold] to see them, or clear your snippets dir to start fresh.")
            return

        samples = [
            ("FastAPI dependency injection example", "python", ["fastapi", "di", "web"],
             'from fastapi import Depends, FastAPI\n\napp = FastAPI()\n\ndef get_db():\n    db = {"key": "value"}\n    try:\n        yield db\n    finally:\n        db.close()\n\n@app.get("/")\ndef read_root(db: dict = Depends(get_db)):\n    return {"message": "Hello", "db": db}'),
            ("React useEffect data fetch hook", "typescript", ["react", "hooks", "fetch"],
             'import { useEffect, useState } from "react";\n\ntype Post = { id: number; title: string };\n\nexport function usePosts(url: string) {\n  const [posts, setPosts] = useState<Post[]>([]);\n  const [loading, setLoading] = useState(true);\n  useEffect(() => {\n    let cancelled = false;\n    setLoading(true);\n    fetch(url).then((res) => res.json()).then((data) => {\n      if (!cancelled) { setPosts(data); setLoading(false); }\n    });\n    return () => { cancelled = true; };\n  }, [url]);\n  return { posts, loading };\n}'),
            ("Python requests with retry", "python", ["requests", "retry", "http"],
             'import requests\nfrom requests.adapters import HTTPAdapter\nfrom urllib3.util.retry import Retry\n\ndef requests_session():\n    session = requests.Session()\n    retries = Retry(total=4, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])\n    session.mount("https://", HTTPAdapter(max_retries=retries))\n    return session'),
            ("SQLAlchemy async session factory", "python", ["sqlalchemy", "async", "database"],
             'from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine\nfrom sqlalchemy.orm import sessionmaker\n\nDATABASE_URL = "sqlite+aiosqlite:///./app.db"\nengine = create_async_engine(DATABASE_URL, echo=False, future=True)\nAsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)'),
            ("Go graceful shutdown HTTP server", "go", ["go", "http", "server"],
             'package main\n\nimport (\n\t"context"\n\t"log"\n\t"net/http"\n\t"os"\n\t"os/signal"\n\t"syscall"\n\t"time"\n)\n\nfunc main() {\n\tsrv := &http.Server{Addr: ":8080"}\n\thttp.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {\n\t\tw.Write([]byte("ok"))\n\t})\n\tgo func() {\n\t\tif err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {\n\t\t\tlog.Fatalf("listen: %v", err)\n\t\t}\n\t}()\n\tquit := make(chan os.Signal, 1)\n\tsignal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)\n\t<-quit\n\tlog.Println("shutdown...")\n\tctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)\n\tdefer cancel()\n\tif err := srv.Shutdown(ctx); err != nil {\n\t\tlog.Fatalf("server forced to shutdown: %v", err)\n\t}\n\tlog.Println("server exited")\n}'),
            ("TypeScript zod schema for user input", "typescript", ["zod", "validation", "typescript"],
             'import { z } from "zod";\n\nexport const UserSchema = z.object({\n  id: z.string().uuid(),\n  email: z.string().email(),\n  role: z.enum(["admin", "member", "viewer"]).default("viewer"),\n  metadata: z.record(z.string()).optional(),\n});\n\nexport type User = z.infer<typeof UserSchema>;'),
            ("Rust error handling with anyhow", "rust", ["rust", "error-handling"],
             'use anyhow::{Context, Result};\n\nfn run() -> Result<()> {\n    let path = std::env::var("CONFIG_PATH").context("CONFIG_PATH must be set")?;\n    let text = std::fs::read_to_string(&path).with_context(|| format!("failed to read {path}"))?;\n    println!("{text}");\n    Ok(())\n}\n\nfn main() {\n    if let Err(err) = run() {\n        eprintln!("error: {err:#}");\n    }\n}'),
            ("Bash retry wrapper for flaky commands", "bash", ["bash", "retry", "shell"],
             '#!/usr/bin/env bash\nset -euo pipefail\n\nretry() {\n  local max=${1:-3}\n  local delay=${2:-1}\n  local attempt=1\n  until "$@"; do\n    if (( attempt >= max )); then\n      echo "failed after ${attempt} attempts" >&2\n      return 1\n    fi\n    echo "attempt ${attempt} failed, retrying in ${delay}s..." >&2\n    sleep "${delay}"\n    ((attempt++))\n  done\n}\n\nretry 5 2 curl -fsS https://httpbin.org/get'),
        ]

        console.print("[bold green]Seeding sample snippets...[/bold green]")
        for title, lang, tags, content in samples:
            try:
                lang_enum = Language(lang)
            except ValueError:
                lang_enum = Language.UNKNOWN
            snippet = Snippet(content=content, metadata=SnippetMetadata(title=title, language=lang_enum), tags=tags)
            storage.save(snippet)
            console.print(f"  [green]✓[/green] {title}")

        console.print("\n[bold]Sample search (semantic):[/bold]")
        try:
            searcher = HybridSearch(config)
            if searcher.indices_ready:
                query = "async python"
                results = searcher.search(query, top_k=3)
                if results:
                    console.print(f"[dim]Query:[/dim] [bold]'{query}'[/bold]")
                    for idx, result in enumerate(results, 1):
                        console.print(f"  [{idx}] {result.snippet.metadata.title} (score: {result.score:.3f})")
                else:
                    console.print("[dim]No results[/dim]")
            else:
                console.print("[dim]No search index available. Run sc build-index after adding snippets.[/dim]")
        except Exception as exc:
            console.print(f"[dim]Demo search skipped: {exc}[/dim]")

        console.print("\n[bold]Sample export (generic):[/bold]")
        try:
            from snipcontext.plugins.base import PluginManager
            pm = PluginManager()
            pm.load_builtin_providers()
            provider = pm.get_provider("generic")
            saved = storage.list_all()
            console.print(Markdown(provider.export_batch(saved)))
        except Exception as exc:
            console.print(f"[dim]Demo export skipped: {exc}[/dim]")

        console.print("\n[bold cyan]Next steps:[/bold cyan]")
        console.print("  - [bold]sc list[/bold]              Review seeded snippets")
        console.print("  - [bold]sc search DI in Python[/bold]  Try semantic search")
        console.print("  - [bold]sc add[/bold] 'your code'...  Add your own")
        console.print("  - [bold]sc build-index[/bold]           Enable semantic search")
