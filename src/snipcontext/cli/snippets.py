"""Snippet domain CLI commands.

Handles add, get, list, edit, delete commands.
Each handler is a thin wrapper that parses args, calls core functions, and formats output.
"""

import logging
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.syntax import Syntax
from rich.table import Table

from snipcontext.cli.context import get_context as _get_context
from snipcontext.core.models import Language, Snippet, SnippetMetadata
from snipcontext.core.storage import SnippetNotFoundError

logger = logging.getLogger(__name__)
console = Console()

# Extension-to-language mapping
_EXT_LANG_MAP: dict[str, str] = {
    "py": "python", "js": "javascript", "ts": "typescript", "jsx": "jsx",
    "tsx": "tsx", "html": "html", "css": "css", "java": "java", "go": "go",
    "rs": "rust", "cpp": "cpp", "c": "c", "cs": "csharp", "php": "php",
    "rb": "ruby", "swift": "swift", "sql": "sql", "sh": "bash", "yml": "yaml",
    "yaml": "yaml", "json": "json", "toml": "toml", "md": "markdown",
    "dockerfile": "dockerfile", "tf": "terraform",
}


def _print_snippet(snippet: Snippet, score: float | None = None, idx: int | None = None) -> None:
    """Pretty-print a snippet with Rich."""
    prefix = f"[{idx}] " if idx else ""
    score_text = f" (score: {score:.3f})" if score else ""
    console.print(
        f"\n[bold yellow]{prefix}[/bold yellow][bold cyan]{snippet.metadata.title}[/bold cyan][dim]{score_text}[/dim]"
    )
    if snippet.metadata.description:
        console.print(f"[dim]Description:[/dim] {snippet.metadata.description}")
    console.print(f"[dim]Language:[/dim] {snippet.metadata.language.value}")
    if snippet.tags:
        console.print(f"[dim]Tags:[/dim] {snippet.tag_line}")
    console.print(f"[dim]ID:[/dim] {snippet.id}")
    console.print()
    lang = snippet.metadata.language.value if snippet.metadata.language.value != "unknown" else "text"
    syntax = Syntax(snippet.content, lang, theme="monokai", line_numbers=False, word_wrap=True)
    console.print(syntax)
    console.print()


def _confirm_action(message: str) -> bool:
    return typer.confirm(message, default=False)


def _accept_auto_tags(merged_tags: list[str], existing_tags: list[str]) -> list[str] | None:
    console.print(f"[yellow]Suggested tags: {', '.join(merged_tags)}[/yellow]")
    choice = typer.prompt("Accept all, keep existing, or enter tags", default="a", show_default=True).strip().lower()
    if choice in {"a", "accept", "y", "yes"}:
        return merged_tags
    if choice in {"e", "existing", "k", "keep"}:
        return existing_tags
    if not choice:
        return None
    custom = [part.strip() for part in choice.replace(",", " ").split() if part.strip()]
    return sorted({*existing_tags, *custom}) if custom else None


def register_commands(app: typer.Typer) -> None:
    """Register snippet management commands."""

    @app.command()
    def add(
        content: str | None = typer.Argument(None, help="Code content or path to file"),
        title: str = typer.Option("", "--title", help="Snippet title"),
        description: str = typer.Option("", "--desc", "-d", help="Short description"),
        language: str = typer.Option("", "--lang", "-l", help="Programming language"),
        tags: list[str] = typer.Option([], "--tag", help="Tags (repeatable)"),
        from_file: bool = typer.Option(False, "--file", "-F", help="Read content from file path"),
        encrypt: bool = typer.Option(False, "--encrypt", "-e", help="Encrypt content"),
        sensitive: bool = typer.Option(False, "--sensitive", help="Mark as sensitive"),
    ) -> None:
        """Add a new code snippet to your collection."""
        config, storage, search = _get_context()
        if sensitive:
            encrypt = True
        if content is None:
            if not sys.stdin.isatty():
                content = sys.stdin.read()
            else:
                console.print("[red]Error: No content provided.[/red]")
                raise typer.Exit(1)
        if from_file:
            path = Path(content)
            if not path.exists():
                console.print(f"[red]File not found: {content}[/red]")
                raise typer.Exit(1)
            content = path.read_text()
            if not title:
                title = path.stem
            if not language:
                language = _EXT_LANG_MAP.get(path.suffix.lstrip(".").lower(), "")
        if not title:
            title = content.strip().split("\n")[0][:50] or "Untitled Snippet"
        if not content.strip():
            console.print("[red]Error: Content cannot be empty.[/red]")
            raise typer.Exit(1)
        try:
            lang_enum = Language(language) if language else Language.UNKNOWN
        except ValueError:
            lang_enum = Language.UNKNOWN
        if encrypt:
            if not config.encryption.enabled:
                console.print("[red]Encryption is not enabled.[/red]")
                raise typer.Exit(1)
            encrypted = storage.encrypt_content(content)
            snippet = Snippet(content="", encrypted_content=encrypted,
                metadata=SnippetMetadata(title=title, description=description, language=lang_enum), tags=tags)
            console.print(f"[green]Added encrypted snippet:[/green] [bold]{snippet.metadata.title}[/bold]")
        else:
            snippet = Snippet(content=content,
                metadata=SnippetMetadata(title=title, description=description, language=lang_enum), tags=tags)
        # Auto-tag and dedup
        final_tags = list(snippet.tags)
        auto_tag_enabled = getattr(getattr(config, "auto_tag", None), "enabled", False)
        dedup_enabled = getattr(getattr(config, "dedup", None), "enabled", False)
        if (auto_tag_enabled or dedup_enabled) and not encrypt:
            try:
                from snipcontext.core.auto_tag import AutoTagService
            except Exception:
                pass
            else:
                embedding = None
                if auto_tag_enabled:
                    service = AutoTagService(vector_index=search.vector_index, storage=storage, config=config.auto_tag)
                    try:
                        embedding = search.embedder.encode_query(snippet.to_search_text()).flatten()
                    except Exception:
                        pass
                    else:
                        suggested = service.suggest(embedding.tolist())
                        if suggested:
                            merged = sorted({*final_tags, *suggested})
                            if config.auto_tag.auto_accept:
                                final_tags = merged
                            else:
                                accepted = _accept_auto_tags(merged, final_tags)
                                if accepted is not None:
                                    final_tags = accepted
                if dedup_enabled and embedding is None:
                    try:
                        embedding = search.embedder.encode_query(snippet.to_search_text()).flatten()
                    except Exception:
                        pass
                if dedup_enabled and embedding is not None:
                    try:
                        neighbors = search.vector_index.search(embedding.reshape(1, -1), top_k=1) if getattr(search.vector_index, "is_trained", False) else []
                    except Exception:
                        neighbors = []
                    if neighbors:
                        neighbor_id, score = neighbors[0]
                        if score >= config.dedup.threshold:
                            try:
                                neighbor = storage.get(neighbor_id)
                                nt = neighbor.metadata.title
                            except Exception:
                                nt = neighbor_id
                            console.print(f"[yellow]This looks similar to '{nt}' (id: {neighbor_id}). Add anyway?[/yellow]")
                            if not config.dedup.auto_accept and not typer.confirm("Add anyway?", default=False):
                                raise typer.Exit(0)
        snippet = snippet.model_copy(update={"tags": final_tags})
        storage.save(snippet)
        console.print(f"[green]Added snippet:[/green] [bold]{snippet.metadata.title}[/bold]")
        console.print(f"   [dim]ID: {snippet.id}[/dim]")
        console.print(f"   [dim]Tags: {snippet.tag_line or '(none)'}[/dim]")

    @app.command()
    def get(
        snippet_id: str = typer.Argument(..., help="Snippet ID or prefix"),
        raw: bool = typer.Option(False, "--raw", "-r", help="Print only code, no metadata"),
    ) -> None:
        """Retrieve a snippet by ID."""
        config, storage, _ = _get_context()
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

    @app.command("list")
    def list_snippets(
        tag: str | None = typer.Option(None, "--tag", help="Filter by tag"),
        language: str | None = typer.Option(None, "--lang", "-l", help="Filter by language"),
        sort: str = typer.Option("updated", "--sort", "-s", help="Sort by: updated, created, title, access"),
    ) -> None:
        """List all snippets with optional filters."""
        config, storage, _ = _get_context()
        snippets = storage.list_all()
        if tag:
            tag = tag.strip().lstrip("#").lower()
            snippets = [s for s in snippets if tag in s.tags]
        if language:
            snippets = [s for s in snippets if s.metadata.language.value == language.lower()]
        sort_key = {"updated": lambda s: s.updated_at, "created": lambda s: s.created_at,
            "title": lambda s: s.metadata.title.lower(), "access": lambda s: s.access_count,
        }.get(sort, lambda s: s.updated_at)
        snippets.sort(key=sort_key, reverse=(sort in ("updated", "created", "access")))
        if not snippets:
            console.print("[yellow]No snippets found.[/yellow]")
            return
        table = Table(title=f"Snippets ({len(snippets)} total)", show_header=True, header_style="bold magenta", row_styles=["", "dim"])
        table.add_column("ID", style="dim", no_wrap=True, width=8)
        table.add_column("Title", style="cyan", no_wrap=False)
        table.add_column("Language", style="green", width=12)
        table.add_column("Tags", style="yellow", width=20)
        table.add_column("Updated", style="dim", width=10)
        from datetime import datetime
        for s in snippets:
            updated = s.updated_at.strftime("%Y-%m-%d") if isinstance(s.updated_at, datetime) else "?"
            table.add_row(s.id[:6], s.metadata.title, s.metadata.language.value,
                ", ".join(s.tags[:3]) + ("..." if len(s.tags) > 3 else ""), updated)
        console.print(table)

    @app.command()
    def edit(
        snippet_id: str = typer.Argument(..., help="Snippet ID or prefix"),
        content: str | None = typer.Option(None, "--content", "-c", help="New code content"),
        title: str | None = typer.Option(None, "--title", help="New title"),
        description: str | None = typer.Option(None, "--desc", "-d", help="New description"),
        add_tags: list[str] = typer.Option([], "--add-tag", help="Add tags"),
        remove_tags: list[str] = typer.Option([], "--remove-tag", help="Remove tags"),
        message: str = typer.Option("", "--message", help="Version bump message"),
    ) -> None:
        """Edit an existing snippet."""
        config, storage, _ = _get_context()
        try:
            snippet = storage.get(snippet_id)
        except SnippetNotFoundError as err:
            console.print(f"[red]Snippet not found: {snippet_id}[/red]")
            raise typer.Exit(1) from err
        snippet.bump_version(message or f"Edit: {title or 'metadata update'}")
        if content: snippet.content = content
        if title: snippet.metadata.title = title
        if description: snippet.metadata.description = description
        for t in add_tags: snippet.merge_tags([t])
        for t in remove_tags:
            t = t.strip().lstrip("#").lower()
            if t in snippet.tags:
                snippet.tags.remove(t)
                snippet.tags.sort()
        snippet.touch()
        storage.save(snippet)
        console.print(f"[green]Updated:[/green] {snippet.metadata.title} [dim]({snippet_id})[/dim]")

    @app.command()
    def delete(
        snippet_id: str,
        force: bool = typer.Option(False, help="Skip confirmation"),
    ) -> None:
        """Delete a snippet."""
        config, storage, _ = _get_context()
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
