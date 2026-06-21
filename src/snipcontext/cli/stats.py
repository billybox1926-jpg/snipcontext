"""Stats and demo CLI commands."""

import json
import logging

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from snipcontext.cli.context import get_context as _get_context

logger = logging.getLogger(__name__)
console = Console()


def _format_size(size_bytes: int) -> str:
    """Format bytes into human-readable size."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes / (1024 * 1024):.1f} MB"


def _render_ascii_bar(data: dict[str, int], max_width: int = 30) -> list[str]:
    """Format a dict of label->count as ASCII bar chart lines."""
    if not data:
        return ["  (no data)"]
    from snipcontext.core.analytics import format_ascii_bar

    return format_ascii_bar(data, max_width)


def _render_basic_stats(s: dict) -> None:
    """Render basic stats mode with Rich."""
    total = s["total_snippets"]

    # Language distribution
    lang_lines = _render_ascii_bar(s.get("languages", {}))
    lang_section = "\n".join(lang_lines) if lang_lines else "  (no snippets)"

    # Top tags
    top_tags = dict(list(s.get("tags", {}).items())[:10])
    tag_lines = [f"  #{tag:<20} {count}" for tag, count in top_tags.items()]
    tag_section = "\n".join(tag_lines) if tag_lines else "  (no tags)"

    # Dates
    nl = "\n"
    date_section = ""
    if s.get("oldest"):
        date_section = f"  Oldest: {s['oldest'][:10]}"
    if s.get("newest"):
        date_section += (
            f"{nl}  Newest: {s['newest'][:10]}" if date_section else f"  Newest: {s['newest'][:10]}"
        )

    date_block = ""
    if date_section:
        date_block = f"[bold]Dates:[/bold]{nl}{date_section}"

    console.print(
        Panel(
            f"""[bold]Collection Overview[/bold]
  Snippets: [cyan]{total}[/cyan]
  Unique Tags: [cyan]{s.get("total_tags", 0)}[/cyan]
  Languages: [cyan]{len(s.get("languages", {}))}[/cyan]
  Encrypted: [cyan]{s.get("encrypted_count", 0)}[/cyan]
  Size: [cyan]{_format_size(s.get("total_size_bytes", 0))}[/cyan]
{date_block}

[bold]By Language:[/bold]
{lang_section}

[bold]Top Tags:[/bold]
{tag_section}

[bold]Storage:[/bold]
  Data directory: [dim]{s.get("data_dir", "N/A")}[/dim]""",
            title="SnipContext Stats",
            border_style="green",
        )
    )


def _render_detailed_stats(d: dict) -> None:
    """Render detailed stats mode with Rich tables and bar charts."""
    total = d["total_snippets"]

    console.print(
        Panel(
            f"""[bold]Collection Overview[/bold]
  Snippets: [cyan]{total}[/cyan]
  Unique Tags: [cyan]{d.get("total_tags", 0)}[/cyan]
  Languages: [cyan]{len(d.get("languages", {}))}[/cyan]
  Encrypted: [cyan]{d.get("encrypted_count", 0)}[/cyan]
  Deleted: [cyan]{d.get("deleted_count", 0)}[/cyan]
  Size: [cyan]{_format_size(d.get("total_size_bytes", 0))}[/cyan]
  Avg tags/snippet: [cyan]{d.get("avg_tags_per_snippet", 0)}[/cyan]""",
            title="SnipContext Stats [bold cyan](Detailed)[/bold cyan]",
            border_style="green",
        )
    )

    # Dates and recent activity
    dates_section = ""
    if d.get("oldest"):
        dates_section = f"  Oldest snippet:  [dim]{d['oldest'][:10]}[/dim]\n"
    if d.get("newest"):
        dates_section += f"  Newest snippet:  [dim]{d['newest'][:10]}[/dim]\n"
    recent = d.get("recent", {})
    if recent:
        dates_section += f"  Added this week:  [cyan]{recent.get('this_week', 0)}[/cyan]\n"
        dates_section += f"  Added this month: [cyan]{recent.get('this_month', 0)}[/cyan]\n"
        dates_section += f"  Added last 3mo:   [cyan]{recent.get('last_3_months', 0)}[/cyan]"
    if dates_section:
        console.print(f"\n[bold]Timeline:[/bold]\n{dates_section}")

    # Language distribution with bar chart
    lang_dist = d.get("language_distribution", {})
    if lang_dist:
        lang_bar_data = {lang: info["count"] for lang, info in list(lang_dist.items())[:10]}
        bar_lines = _render_ascii_bar(lang_bar_data, max_width=25)
        console.print("\n[bold]Language Distribution:[/bold]")
        for line in bar_lines:
            lang_name = line.split("\u2588")[0].strip() if "\u2588" in line else line
            bar_part = line[line.index("\u2588") :] if "\u2588" in line else ""
            count = bar_part.split()[-1] if bar_part.strip() else ""
            # Reformat with percentage
            lang_key = lang_name.strip()
            if lang_key in lang_dist:
                pct = lang_dist[lang_key]["percent"]
                console.print(f"  {lang_name:<16} {bar_part} ({pct}%)")
            else:
                console.print(line)

    # Tag distribution
    tags = d.get("tags", {})
    top_tags = dict(list(tags.items())[:10])
    if top_tags:
        tag_bar_lines = _render_ascii_bar(top_tags, max_width=20)
        console.print("\n[bold]Top Tags:[/bold]")
        for line in tag_bar_lines:
            console.print(line)

    # Access counts
    access = d.get("access_counts", {})
    if access and (access.get("most_accessed") or access.get("average", 0) > 0):
        console.print("\n[bold]Access Stats:[/bold]")
        console.print(f"  Average accesses per snippet: [cyan]{access.get('average', 0)}[/cyan]")
        most = access.get("most_accessed", [])
        if most:
            table = Table(show_header=True, header_style="bold magenta", padding=(0, 1))
            table.add_column("ID", style="dim", width=8)
            table.add_column("Title", style="cyan", no_wrap=False)
            table.add_column("Accesses", style="green", justify="right", width=8)
            for entry in most:
                table.add_row(entry["id"], entry["title"], str(entry["count"]))
            console.print(table)

    # Size metrics
    size = d.get("size_metrics", {})
    if size and size.get("largest"):
        console.print("\n[bold]Size Metrics:[/bold]")
        console.print(f"  Average lines per snippet: [cyan]{size.get('average_lines', 0)}[/cyan]")
        console.print(f"  Average characters:        [cyan]{size.get('average_chars', 0)}[/cyan]")
        table = Table(show_header=True, header_style="bold magenta", padding=(0, 1))
        table.add_column("ID", style="dim", width=8)
        table.add_column("Title", style="cyan", no_wrap=False)
        table.add_column("Lines", style="green", justify="right", width=6)
        table.add_column("Chars", style="green", justify="right", width=8)
        for entry in size["largest"]:
            table.add_row(entry["id"], entry["title"], str(entry["lines"]), str(entry["chars"]))
        console.print(table)

    # Confidence breakdown
    confidence = d.get("confidence", {})
    if confidence:
        console.print("\n[bold]Confidence Levels:[/bold]")
        for level, count in confidence.items():
            console.print(f"  {level:<16} {count}")

    # Version statistics
    versions = d.get("versions", {})
    if versions:
        console.print("\n[bold]Version History:[/bold]")
        console.print(f"  Average versions per snippet: [cyan]{versions.get('average', 0)}[/cyan]")
        console.print(f"  Max versions in a snippet:    [cyan]{versions.get('max', 0)}[/cyan]")

    # Authors
    authors = d.get("authors", {})
    if authors and len(authors) > 1:
        console.print("\n[bold]Authors:[/bold]")
        for author, count in authors.items():
            console.print(f"  {author:<24} {count}")


def register_commands(app: typer.Typer) -> None:
    """Register stats and demo commands on the given Typer app."""

    @app.command()  # type: ignore[untyped-decorator]
    def stats(
        detailed: bool = typer.Option(False, "--detailed", "-d", help="Show detailed analytics"),
        json_output: bool = typer.Option(False, "--json", help="Output stats as JSON"),
    ) -> None:
        """Show collection statistics."""
        config, storage, _ = _get_context()
        snippets = storage.list_all()

        # Inject storage paths into basic stats
        basic = storage.get_stats()
        basic["data_dir"] = str(config.storage.data_dir)

        if json_output:
            if detailed:
                from snipcontext.core.analytics import compute_detailed_stats

                output = compute_detailed_stats(snippets)
                output["data_dir"] = str(config.storage.data_dir)
            else:
                output = basic
            console.print(json.dumps(output, indent=2, default=str))
            return

        if len(snippets) == 0:
            console.print("[yellow]No snippets in your collection yet.[/yellow]")
            console.print("Add one with: [bold]sc add 'your code here' --title 'My Snippet'[/bold]")
            return

        if detailed:
            from snipcontext.core.analytics import compute_detailed_stats

            detailed_stats = compute_detailed_stats(snippets)
            detailed_stats["data_dir"] = str(config.storage.data_dir)
            _render_detailed_stats(detailed_stats)
        else:
            _render_basic_stats(basic)

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
                'import { useEffect, useState } from "react";\n\ntype Post = { id: number; title: string };\n\nexport function usePosts(url: string) {\n  const [posts, setPosts] = useState<Post[]>([]);\n  const [loading, setLoading] = useState(true);\n  useEffect(() => {\n    let cancelled = false;\n    setLoading(true);\n    fetch(url).then((res) => res.json()).then((data) => {\n      if (!cancelled) { setPosts(data); setLoading(false); }\n    });\n    return () => { cancelled = true; };\n  }, [url]);\n  return { posts, loading };\n}',
            ),
            (
                "Python requests with retry",
                "python",
                ["requests", "retry", "http"],
                'import requests\nfrom requests.adapters import HTTPAdapter\nfrom urllib3.util.retry import Retry\n\ndef requests_session():\n    session = requests.Session()\n    retries = Retry(total=4, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])\n    session.mount("https://", HTTPAdapter(max_retries=retries))\n    return session',
            ),
            (
                "SQLAlchemy async session factory",
                "python",
                ["sqlalchemy", "async", "database"],
                'from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine\nfrom sqlalchemy.orm import sessionmaker\n\nDATABASE_URL = "sqlite+aiosqlite:///./app.db"\nengine = create_async_engine(DATABASE_URL, echo=False, future=True)\nAsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)',
            ),
            (
                "Go graceful shutdown HTTP server",
                "go",
                ["go", "http", "server"],
                'package main\n\nimport (\n\t"context"\n\t"log"\n\t"net/http"\n\t"os"\n\t"os/signal"\n\t"syscall"\n\t"time"\n)\n\nfunc main() {\n\tsrv := &http.Server{Addr: ":8080"}\n\thttp.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {\n\t\tw.Write([]byte("ok"))\n\t})\n\tgo func() {\n\t\tif err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {\n\t\t\tlog.Fatalf("listen: %v", err)\n\t\t}\n\t}()\n\tquit := make(chan os.Signal, 1)\n\tsignal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)\n\t<-quit\n\tlog.Println("shutdown...")\n\tctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)\n\tdefer cancel()\n\tif err := srv.Shutdown(ctx); err != nil {\n\t\tlog.Fatalf("server forced to shutdown: %v", err)\n\t}\n\tlog.Println("server exited")\n}',
            ),
            (
                "TypeScript zod schema for user input",
                "typescript",
                ["zod", "validation", "typescript"],
                'import { z } from "zod";\n\nexport const UserSchema = z.object({\n  id: z.string().uuid(),\n  email: z.string().email(),\n  role: z.enum(["admin", "member", "viewer"]).default("viewer"),\n  metadata: z.record(z.string()).optional(),\n});\n\nexport type User = z.infer<typeof UserSchema>;',
            ),
            (
                "Rust error handling with anyhow",
                "rust",
                ["rust", "error-handling"],
                'use anyhow::{Context, Result};\n\nfn run() -> Result<()> {\n    let path = std::env::var("CONFIG_PATH").context("CONFIG_PATH must be set")?;\n    let text = std::fs::read_to_string(&path).with_context(|| format!("failed to read {path}"))?;\n    println!("{text}");\n    Ok(())\n}\n\nfn main() {\n    if let Err(err) = run() {\n        eprintln!("error: {err:#}");\n    }\n}',
            ),
            (
                "Bash retry wrapper for flaky commands",
                "bash",
                ["bash", "retry", "shell"],
                '#!/usr/bin/env bash\nset -euo pipefail\n\nretry() {\n  local max=${1:-3}\n  local delay=${2:-1}\n  local attempt=1\n  until "$@"; do\n    if (( attempt >= max )); then\n      echo "failed after ${attempt} attempts" >&2\n      return 1\n    fi\n    echo "attempt ${attempt} failed, retrying in ${delay}s..." >&2\n    sleep "${delay}"\n    ((attempt++))\n  done\n}\n\nretry 5 2 curl -fsS https://httpbin.org/get',
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
                metadata=SnippetMetadata(title=title, language=lang_enum),
                tags=tags,
            )
            storage.save(snippet)
            console.print(f"  [green]+[/green] {title}")

        console.print("\n[bold]Sample search (semantic):[/bold]")
        try:
            searcher = HybridSearch(config)
            if searcher.indices_ready:
                query = "async python"
                results = searcher.search(query, top_k=3)
                if results:
                    console.print(f"[dim]Query:[/dim] [bold]'{query}'[/bold]")
                    for idx, result in enumerate(results, 1):
                        console.print(
                            f"  [{idx}] {result.snippet.metadata.title} (score: {result.score:.3f})"
                        )
                else:
                    console.print("[dim]No results[/dim]")
            else:
                console.print(
                    "[dim]No search index available. Run sc build-index after adding snippets.[/dim]"
                )
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
