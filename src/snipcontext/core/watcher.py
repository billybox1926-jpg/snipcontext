"""Filesystem watcher integration for SnipContext.

Monitors the snippets directory using watchdog and triggers incremental
search index rebuilds so new/edited/deleted snippets are reflected
without a manual reindex. Respects the ``watchdog_enabled`` config toggle
and degrades gracefully when watchdog is not installed.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


try:  # pragma: no cover - optional dependency
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer

    _WATCHDOG_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dependency
    _WATCHDOG_AVAILABLE = False
    FileSystemEventHandler = object  # type: ignore[misc,assignment]
    Observer = None  # type: ignore[assignment,misc]


class SnippetChangeHandler(FileSystemEventHandler):
    """React to snippet file changes by rebuilding the search index."""

    def __init__(self, search_engine, storage_engine) -> None:
        self.search = search_engine
        self.storage = storage_engine

    def on_any_event(self, event) -> None:
        """Handle any filesystem event by triggering an incremental reindex.

        Skips directory events and temporary files.
        """
        if event.is_directory or str(event.src_path).endswith(".tmp"):
            return
        try:
            snippets = self.storage.list_all()
        except Exception as exc:
            logger.debug("Watcher handler skipped update: %s", exc)
            return
        self.search.rebuild_incremental(snippets)


class SnippetWatcher:
    """Filesystem watcher that keeps the search index in sync with snippets."""

    def __init__(self, config, search_engine, storage_engine) -> None:
        self.config = config
        self.search = search_engine
        self.storage = storage_engine
        self.observer = None

    def start(self) -> None:
        """Begin watching the snippets directory for changes.

        Does nothing if ``watchdog_enabled`` is ``False`` in config.
        Gracefully handles watchdog not being installed.
        """
        if not getattr(self.config, "watchdog_enabled", True):
            print("Watchdog disabled in config. Exiting.")
            return
        if not _WATCHDOG_AVAILABLE:
            print("watchdog not installed. Install with: pip install watchdog")
            return

        handler = SnippetChangeHandler(self.search, self.storage)
        self.observer = Observer()
        self.observer.schedule(handler, str(self.config.snippets_path), recursive=False)
        self.observer.start()
        print(f"Watching {self.config.snippets_path} for changes...")
        try:
            while self.observer.is_alive():
                self.observer.join(1)
        except KeyboardInterrupt:
            self.observer.stop()
            self.observer.join()
        print("Watcher stopped.")
