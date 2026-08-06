"""Import domain CLI commands."""

from __future__ import annotations

import logging
import urllib.parse
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel

from snipcontext.cli.context import get_context as _get_context
from snipcontext.core.importers import parse_yaml_import
from snipcontext.core.storage import StorageError

logger = logging.getLogger(__name__)
console = Console()


def register_commands(app: typer.Typer) -> None:
    @app.command()  # type: ignore[untyped-decorator]
    def import_(
        url: str = typer.Argument(..., help="URL or https:// URL to a YAML snippet collection"),
        dry_run: bool = typer.Option(False, "--dry-run", help="Preview snippets without importing"),
    ) -> None:
        """Import snippets from a remote YAML file."""
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in {"", "https"}:
            console.print("[red]Only https:// URLs are supported for remote imports.[/red]")
            raise typer.Exit(1)

        console.print(f"[bold]Importing from:[/bold] {url}")
        if dry_run:
            console.print("[yellow]Dry run enabled; no snippets will be written.[/yellow]")

        try:
            if parsed.scheme == "https":
                try:
                    import httpx  # noqa: F401
                except ModuleNotFoundError as exc:
                    raise RuntimeError(
                        "Remote import requires the web extra. "
                        "Install with: pip install snipcontext[web]"
                    ) from exc
                import httpx

                try:
                    with httpx.Client(timeout=30) as client:
                        response = client.get(url)
                        response.raise_for_status()
                        raw = response.text
                except Exception as exc:
                    console.print(f"[red]Failed to fetch remote file:[/red] {exc}")
                    raise typer.Exit(1) from exc
            else:
                path = Path(url)
                raw = path.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            console.print(f"[red]File not found:[/red] {exc}")
            raise typer.Exit(1) from exc
        except OSError as exc:
            console.print(f"[red]Failed to read source:[/red] {exc}")
            raise typer.Exit(1) from exc

        try:
            snippets = parse_yaml_import(raw)
        except ValueError as exc:
            console.print(f"[red]Invalid import format:[/red] {exc}")
            raise typer.Exit(1) from exc
        except Exception as exc:
            console.print(f"[red]Failed to parse import:[/red] {exc}")
            raise typer.Exit(1) from exc

        if not snippets:
            console.print("[yellow]No snippets found in source.[/yellow]")
            raise typer.Exit(0)

        console.print(f"[green]Found {len(snippets)} snippet(s) to import.[/green]")

        if dry_run:
            for item in snippets:
                console.print(
                    Panel(
                        f"[bold]{item.title}[/bold]\n{item.content}",
                        title=f"{item.language} — {', '.join(item.tags) or 'no tags'}",
                    )
                )
            return

        config, storage, _ = _get_context()
        imported = 0
        for item in snippets:
            snippet = Snippet(
                content=item.content,
                metadata=SnippetMetadata(
                    title=item.title,
                    description="",
                    language=item.language,
                ),
                tags=item.tags,
            )
            try:
                existing = storage.find_by_content_hash(snippet.content_hash)
            except Exception:
                existing = None
            if existing:
                console.print(
                    f"[yellow]Skipping duplicate:[/yellow] {item.title} (id: {existing.id})"
                )
                continue
            storage.save(snippet)
            imported += 1
            console.print(f"[green]Imported:[/green] {item.title}")

        console.print(f"[bold]Done.[/bold] Imported {imported} snippet(s).")
