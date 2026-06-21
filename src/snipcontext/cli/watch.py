"""Watch domain CLI commands."""

import logging

import typer
from rich.console import Console

from snipcontext.cli.context import get_context as _get_context
from snipcontext.core.watcher import SnippetWatcher

logger = logging.getLogger(__name__)
console = Console()


def register_commands(app: typer.Typer) -> None:
    """Register file watcher commands."""

    @app.command()  # type: ignore[untyped-decorator]
    def watch() -> None:
        """Watch snippet directory for changes and auto-update the search index."""
        config, storage, search = _get_context()
        watcher = SnippetWatcher(config, search, storage)
        watcher.start()
