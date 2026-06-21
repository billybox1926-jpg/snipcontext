"""Crypto domain CLI commands."""

import logging

import typer
from rich.console import Console

from snipcontext.cli.context import get_context as _get_context
from snipcontext.core.storage import SnippetNotFoundError

logger = logging.getLogger(__name__)
console = Console()


def register_commands(app: typer.Typer) -> None:
    """Register encryption commands."""

    @app.command()  # type: ignore[untyped-decorator]
    def encrypt(
        snippet_id: str = typer.Argument(..., help="Snippet ID to encrypt"),
    ) -> None:
        """Encrypt a snippet's content for secure storage."""
        config, storage, _ = _get_context()
        if not config.encryption.enabled:
            console.print(
                "[red]Encryption is not enabled. Set SNIPCONTEXT_ENCRYPT_ENABLED=true[/red]"
            )
            console.print(
                "[dim]See: https://github.com/billybox1926-jpg/snipcontext/wiki/Encryption[/dim]"
            )
            raise typer.Exit(1)
        try:
            snippet = storage.get(snippet_id)
        except SnippetNotFoundError:
            console.print(f"[red]Snippet not found: {snippet_id}[/red]")
            raise typer.Exit(1) from None
        if snippet.encrypted_content:
            console.print("[yellow]Snippet already encrypted[/yellow]")
            return
        try:
            encrypted = storage.encrypt_content(snippet.content)
            snippet.encrypted_content = encrypted
            snippet.content = ""
            storage.save(snippet)
            console.print(f"[green]Encrypted snippet: {snippet.metadata.title}[/green]")
        except Exception as exc:
            console.print(f"[red]Encryption failed: {exc}[/red]")
            raise typer.Exit(1) from exc

    @app.command()  # type: ignore[untyped-decorator]
    def decrypt(
        snippet_id: str = typer.Argument(..., help="Snippet ID to decrypt"),
    ) -> None:
        """Decrypt a snippet's content for viewing/editing."""
        config, storage, _ = _get_context()
        try:
            snippet = storage.get(snippet_id)
        except SnippetNotFoundError:
            console.print(f"[red]Snippet not found: {snippet_id}[/red]")
            raise typer.Exit(1) from None
        if not snippet.encrypted_content:
            console.print("[yellow]Snippet is not encrypted[/yellow]")
            return
        try:
            decrypted = storage.decrypt_content(snippet.encrypted_content)
            snippet.content = decrypted
            snippet.encrypted_content = None
            storage.save(snippet)
            console.print(f"[green]Decrypted snippet: {snippet.metadata.title}[/green]")
        except Exception as exc:
            console.print(f"[red]Decryption failed: {exc}[/red]")
            raise typer.Exit(1) from exc
