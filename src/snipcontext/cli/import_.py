"""Import domain CLI commands."""

from __future__ import annotations

import logging
import urllib.parse
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel

from snipcontext.cli.context import get_context as _get_context
from snipcontext.core.builtin_collections import (
    BUILTIN_COLLECTION_SCHEME,
    is_builtin_collection_source,
    load_builtin_collection,
)
from snipcontext.core.importers import import_tar_gz, parse_import, to_snippet
from snipcontext.core.models import Snippet
from snipcontext.core.storage import StorageError

logger = logging.getLogger(__name__)
console = Console()


def _is_windows_abs_path(url: str) -> bool:
    if len(url) >= 3 and url[1] == ":" and url[2] in ("/", "\\"):
        return True
    if len(url) >= 3 and url[0] == "/" and url[1:2].isalpha() and url[2] in ("/", "\\"):
        return True
    return False


def register_commands(app: typer.Typer) -> None:
    @app.command("import")  # type: ignore[untyped-decorator]
    def import_(
        url: str = typer.Argument(..., help="URL or path to a snippet collection"),
        format: str | None = typer.Option(
            None,
            "--format",
            "-f",
            help="Import format: yaml, json, markdown, tar.gz. Default: auto-detect",
        ),
        preview: bool = typer.Option(
            False,
            "--dry-run",
            "--list",
            help="Preview snippets without importing",
        ),
    ) -> None:
        """Import snippets from a remote or local file."""
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in {
            "",
            "https",
            BUILTIN_COLLECTION_SCHEME,
        } and not _is_windows_abs_path(url):
            console.print(
                "[red]Only https:// URLs or built-in collections are supported for remote imports.[/red]"
            )
            raise typer.Exit(1)

        normalized_format = None
        if format:
            normalized_format = format.lower()
            if normalized_format not in {"yaml", "json", "markdown", "tar.gz"}:
                console.print(
                    f"[red]Unsupported format: {format}. Use yaml, json, markdown, or tar.gz.[/red]"
                )
                raise typer.Exit(1)

        console.print(f"[bold]Importing from:[/bold] {url}")
        if preview:
            console.print("[yellow]Dry run/preview enabled; no snippets will be written.[/yellow]")

        try:
            raw: bytes | str | None = None
            if is_builtin_collection_source(url):
                # Built-in collections are handled separately below.
                raw = None
            elif parsed.scheme == "https":
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
                        if normalized_format == "tar.gz":
                            raw = response.content
                        else:
                            raw = response.text
                except (httpx.HTTPError, OSError) as exc:
                    console.print(f"[red]Failed to fetch remote file:[/red] {exc}")
                    raise typer.Exit(1) from exc
            else:
                path = Path(url)
                if normalized_format == "tar.gz":
                    raw = path.read_bytes()
                else:
                    raw = path.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            console.print(f"[red]File not found:[/red] {exc}")
            raise typer.Exit(1) from exc
        except OSError as exc:
            console.print(f"[red]Failed to read source:[/red] {exc}")
            raise typer.Exit(1) from exc

        if raw is None and not is_builtin_collection_source(url):
            raise RuntimeError("Failed to load source payload")

        try:
            if is_builtin_collection_source(url):
                collection_name = url.split(":", 1)[1]
                snippets = load_builtin_collection(collection_name)
            elif normalized_format == "tar.gz":
                if not isinstance(raw, bytes):
                    raise RuntimeError("Tar.gz source must be binary")
                snippets = import_tar_gz(raw)
            elif (
                normalized_format is None and isinstance(raw, bytes) and raw.startswith(b"\x1f\x8b")
            ):
                snippets = import_tar_gz(raw)
            else:
                if isinstance(raw, str):
                    text = raw
                elif isinstance(raw, bytes):
                    text = raw.decode("utf-8", errors="replace")
                else:
                    raise RuntimeError("Invalid import payload")
                snippets = parse_import(text, format=normalized_format)
        except ValueError as exc:
            console.print(f"[red]Invalid import format:[/red] {exc}")
            raise typer.Exit(1) from exc
        except (RuntimeError, TypeError) as exc:
            console.print(f"[red]Failed to parse import:[/red] {exc}")
            raise typer.Exit(1) from exc

        if not snippets:
            console.print("[yellow]No snippets found in source.[/yellow]")
            raise typer.Exit(0)

        console.print(f"[green]Found {len(snippets)} snippet(s) to import.[/green]")

        if preview:
            for item in snippets:
                console.print(
                    Panel(
                        f"[bold]{item.title}[/bold]\n{item.content}",
                        title=f"{item.language} — {', '.join(item.tags) or 'no tags'}",
                    )
                )
            return

        config, storage, search = _get_context()
        imported_snippets: list[Snippet] = []
        imported = 0
        for item in snippets:
            snippet = to_snippet(item)
            try:
                existing = storage.find_by_content_hash(snippet.content_hash)
            except StorageError:
                existing = None
            if existing:
                console.print(
                    f"[yellow]Skipping duplicate:[/yellow] {item.title} (id: {existing.id})"
                )
                continue
            storage.save(snippet)
            imported_snippets.append(snippet)
            imported += 1
            console.print(f"[green]Imported:[/green] {item.title}")

        if imported_snippets:
            try:
                if search.indices_ready:
                    for snippet in imported_snippets:
                        try:
                            search.add_snippet(snippet)
                        except (StorageError, RuntimeError, OSError):
                            logger.debug("Failed to add imported snippet to index", exc_info=True)
                    try:
                        search.rebuild_keyword_index(storage.list_all())
                    except (StorageError, RuntimeError, OSError):
                        logger.debug("Failed to rebuild keyword index after import", exc_info=True)
                else:
                    search.index_snippets(storage.list_all())
            except (StorageError, RuntimeError, OSError):
                logger.debug("Import indexing failed", exc_info=True)

        console.print(f"[bold]Done.[/bold] Imported {imported} snippet(s).")
