"""Snippet domain CLI commands.

Handles add, get, list, edit, delete commands.
Each handler is a thin wrapper that parses args, calls core functions, and formats output.
"""

import logging
import os
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


def _print_snippet(snippet: Snippet, score: float | None = None, idx: int | None = None) -> None:
    """Pretty-print a snippet with Rich."""
    from snipcontext.core.sanitization import sanitize_for_display

    prefix = f"[{idx}] " if idx else ""
    score_text = f" (score: {score:.3f})" if score else ""
    console.print(
        f"\n[bold yellow]{prefix}[/bold yellow][bold cyan]{snippet.metadata.title}[/bold cyan][dim]{score_text}[/dim]"
    )
    if snippet.metadata.description:
        console.print(
            f"[dim]Description:[/dim] {sanitize_for_display(snippet.metadata.description)}"
        )
    console.print(f"[dim]Language:[/dim] {snippet.metadata.language.value}")
    if snippet.metadata.framework:
        console.print(f"[dim]Framework:[/dim] {snippet.metadata.framework}")
    if snippet.metadata.version:
        console.print(f"[dim]Version:[/dim] {snippet.metadata.version}")
    if snippet.metadata.source_url:
        console.print(f"[dim]Source:[/dim] {snippet.metadata.source_url}")
    if snippet.metadata.custom_tags:
        meta_parts = [f"{k}={v}" for k, v in snippet.metadata.custom_tags.items()]
        console.print(f"[dim]Custom:[/dim] {', '.join(meta_parts)}")
    if snippet.tags:
        console.print(f"[dim]Tags:[/dim] {snippet.tag_line}")
    console.print(f"[dim]ID:[/dim] {snippet.id}")
    console.print()
    lang = (
        snippet.metadata.language.value if snippet.metadata.language.value != "unknown" else "text"
    )
    syntax = Syntax(
        sanitize_for_display(snippet.content),
        lang,
        theme="monokai",
        line_numbers=False,
        word_wrap=True,
    )
    console.print(syntax)
    console.print()


def _confirm_action(message: str) -> bool:
    return typer.confirm(message, default=False)


def _parse_custom(pairs: list[str]) -> dict[str, str]:
    """Parse 'key=value' CLI args into a dict. Silently skips malformed entries."""
    result: dict[str, str] = {}
    for item in pairs:
        if "=" in item:
            key, val = item.split("=", 1)
            result[key.strip()] = val.strip()
    return result


def _accept_auto_tags(merged_tags: list[str], existing_tags: list[str]) -> list[str] | None:
    console.print(f"[yellow]Suggested tags: {', '.join(merged_tags)}[/yellow]")
    choice = (
        typer.prompt("Accept all, keep existing, or enter tags", default="a", show_default=True)
        .strip()
        .lower()
    )
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

    @app.command()  # type: ignore[untyped-decorator]
    def add(
        content: str | None = typer.Argument(None, help="Code content or path to file"),
        title: str = typer.Option("", "--title", help="Snippet title"),
        description: str = typer.Option("", "--desc", "-d", help="Short description"),
        language: str = typer.Option("", "--lang", "-l", help="Programming language"),
        tags: list[str] = typer.Option([], "--tag", help="Tags (repeatable)"),
        source: str = typer.Option(
            "", "--source", help="URL or file path where snippet originated"
        ),
        framework: str = typer.Option(
            "", "--framework", help="Target framework/library (e.g. react, fastapi)"
        ),
        version: str = typer.Option("", "--version", help="Target framework/library version"),
        custom: list[str] = typer.Option(
            [], "--custom", help="Custom key=value metadata (repeatable)"
        ),
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
            try:
                encrypted = storage.encrypt_content(content)
            except Exception as exc:
                console.print(f"[red]Encryption failed: {exc}[/red]")
                raise typer.Exit(1) from exc
            custom_meta = _parse_custom(custom)
            snippet = Snippet(
                content="",
                encrypted_content=encrypted,
                metadata=SnippetMetadata(
                    title=title,
                    description=description,
                    language=lang_enum,
                    source_url=source,
                    framework=framework,
                    version=version,
                    custom_tags=custom_meta,
                ),
                tags=tags,
            )
            console.print(
                f"[green]Added encrypted snippet:[/green] [bold]{snippet.metadata.title}[/bold]"
            )
        else:
            custom_meta = _parse_custom(custom)
            snippet = Snippet(
                content=content,
                metadata=SnippetMetadata(
                    title=title,
                    description=description,
                    language=lang_enum,
                    source_url=source,
                    framework=framework,
                    version=version,
                    custom_tags=custom_meta,
                ),
                tags=tags,
            )
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
                    service = AutoTagService(
                        vector_index=search.vector_index, storage=storage, config=config.auto_tag
                    )
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
                        neighbors = (
                            search.vector_index.search(embedding.reshape(1, -1), top_k=1)
                            if getattr(search.vector_index, "is_trained", False)
                            else []
                        )
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
                            console.print(
                                f"[yellow]This looks similar to '{nt}' (id: {neighbor_id}). Add anyway?[/yellow]"
                            )
                            if not config.dedup.auto_accept and not typer.confirm(
                                "Add anyway?", default=False
                            ):
                                raise typer.Exit(0)
        snippet = snippet.model_copy(update={"tags": final_tags})
        storage.save(snippet)
        console.print(f"[green]Added snippet:[/green] [bold]{snippet.metadata.title}[/bold]")
        console.print(f"   [dim]ID: {snippet.id}[/dim]")
        console.print(f"   [dim]Tags: {snippet.tag_line or '(none)'}[/dim]")

    @app.command()  # type: ignore[untyped-decorator]
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

    @app.command("list")  # type: ignore[untyped-decorator]
    def list_snippets(
        tag: str | None = typer.Option(None, "--tag", help="Filter by tag"),
        language: str | None = typer.Option(None, "--lang", "-l", help="Filter by language"),
        sort: str = typer.Option(
            "updated", "--sort", "-s", help="Sort by: updated, created, title, access"
        ),
    ) -> None:
        """List all snippets with optional filters."""
        config, storage, _ = _get_context()
        snippets = storage.list_all()
        if tag:
            tag = tag.strip().lstrip("#").lower()
            snippets = [s for s in snippets if tag in s.tags]
        if language:
            snippets = [s for s in snippets if s.metadata.language.value == language.lower()]
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
            updated = (
                s.updated_at.strftime("%Y-%m-%d") if isinstance(s.updated_at, datetime) else "?"
            )
            table.add_row(
                s.id[:6],
                s.metadata.title,
                s.metadata.language.value,
                ", ".join(s.tags[:3]) + ("..." if len(s.tags) > 3 else ""),
                updated,
            )
        console.print(table)

    @app.command()  # type: ignore[untyped-decorator]
    def edit(
        snippet_id: str = typer.Argument(..., help="Snippet ID or prefix"),
        content: str | None = typer.Option(None, "--content", "-c", help="New code content"),
        title: str | None = typer.Option(None, "--title", help="New title"),
        description: str | None = typer.Option(None, "--desc", "-d", help="New description"),
        language: str | None = typer.Option(None, "--lang", "-l", help="New language"),
        source: str | None = typer.Option(None, "--source", help="Source URL or file path"),
        framework: str | None = typer.Option(None, "--framework", help="Target framework/library"),
        version: str | None = typer.Option(
            None, "--version", help="Target framework/library version"
        ),
        add_tags: list[str] = typer.Option([], "--tag", "--add-tag", help="Add tags (repeatable)"),
        remove_tags: list[str] = typer.Option([], "--remove-tag", help="Remove tags"),
        custom: list[str] = typer.Option(
            [], "--custom", help="Custom key=value metadata (repeatable)"
        ),
        from_file: bool = typer.Option(False, "--file", "-F", help="Read content from file"),
        interactive: bool = typer.Option(False, "--interactive", "-i", help="Open in $EDITOR"),
        force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation prompt"),
        message: str = typer.Option("", "--message", help="Version bump message"),
    ) -> None:
        """Edit an existing snippet.

        Supports partial updates — only specified fields are changed.
        Use --tag to add tags, --remove-tag to remove them.
        Use --interactive to open the snippet in $EDITOR for full editing.
        """
        from snipcontext.core.snippet_ops import edit_snippet

        config, storage, _ = _get_context()
        try:
            snippet = storage.get(snippet_id)
        except SnippetNotFoundError as err:
            console.print(f"[red]Snippet not found: {snippet_id}[/red]")
            raise typer.Exit(1) from err

        # Resolve content from file
        edit_content = content
        if from_file and content:
            path = Path(content)
            if not path.exists():
                console.print(f"[red]File not found: {content}[/red]")
                raise typer.Exit(1)
            edit_content = path.read_text()
            if not language:
                language = _EXT_LANG_MAP.get(path.suffix.lstrip(".").lower(), "")

        # Interactive mode: open in $EDITOR
        if interactive:
            import tempfile

            editor = os.environ.get("EDITOR", "vi")
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".snippet", prefix="sc-edit-", delete=False
            ) as tmp:
                tmp.write(snippet.content)
                tmp_path = tmp.name
            try:
                os.system(f'{editor} "{tmp_path}"')
                edit_content = Path(tmp_path).read_text()
            finally:
                Path(tmp_path).unlink(missing_ok=True)

            # Detect if content changed
            if edit_content == snippet.content:
                console.print("[yellow]No changes detected. Exiting.[/yellow]")
                raise typer.Exit(0)
            if not language and edit_content:
                # Auto-detect language from content if not specified
                pass

        # Check if any changes were requested
        has_changes = any(
            [
                edit_content is not None,
                title is not None,
                description is not None,
                language is not None,
                source is not None,
                framework is not None,
                version is not None,
                add_tags,
                remove_tags,
                custom,
            ]
        )
        if not has_changes:
            console.print(
                "[yellow]No changes specified. Use options like --title, --content, --tag, etc.[/yellow]"
            )
            raise typer.Exit(0)

        # Build change summary for confirmation
        changes: list[str] = []
        if edit_content is not None:
            changes.append("content")
        if title is not None:
            changes.append(f"title -> {title}")
        if description is not None:
            changes.append("description")
        if language is not None:
            changes.append(f"language -> {language}")
        if source is not None:
            changes.append(f"source -> {source}")
        if framework is not None:
            changes.append(f"framework -> {framework}")
        if version is not None:
            changes.append(f"version -> {version}")
        if add_tags:
            changes.append(f"+tags: {', '.join(add_tags)}")
        if remove_tags:
            changes.append(f"-tags: {', '.join(remove_tags)}")
        if custom:
            changes.append(f"custom: {', '.join(custom)}")

        # Confirmation prompt (unless --force)
        if not force:
            console.print(
                f"[cyan]Editing:[/cyan] {snippet.metadata.title} [dim]({snippet.id})[/dim]"
            )
            console.print(f"  [dim]Changes: {', '.join(changes)}[/dim]")
            if not _confirm_action("Apply these changes?"):
                console.print("Cancelled.")
                raise typer.Exit(0)

        # Delegate to core function
        updated = edit_snippet(
            storage,
            snippet.id,
            content=edit_content,
            title=title,
            description=description,
            language=language or None,
            source=source,
            framework=framework,
            version=version,
            custom_tags=_parse_custom(custom) if custom else None,
            add_tags=add_tags if add_tags else None,
            remove_tags=remove_tags if remove_tags else None,
            message=message,
        )

        console.print(f"[green]Updated:[/green] {updated.metadata.title} [dim]({snippet.id})[/dim]")
        console.print(f"  [dim]Tags: {updated.tag_line or '(none)'}[/dim]")
        console.print(f"  [dim]Language: {updated.metadata.language.value}[/dim]")

    @app.command()  # type: ignore[untyped-decorator]
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
