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
        r"""
        Watch snippet directory for changes and auto-update the search index.

        \b
        Uses watchdog to monitor the snippets directory. When files are
        added, modified, or deleted, the index is updated incrementally.

        \b
        Debounce is enabled by default (2-second window) to avoid
        excessive reindexes during batch changes. Runs in the foreground;
        press Ctrl+C to stop.
        """
        config, storage, search = _get_context()
        watcher = SnippetWatcher(config, search, storage)
        watcher.start()
