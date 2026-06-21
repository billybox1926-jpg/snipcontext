"""Filesystem watcher integration for SnipContext.

Monitors the snippets directory using watchdog and triggers incremental
search index rebuilds so new/edited/deleted snippets are reflected
without a manual reindex. Respects the ``watchdog_enabled`` config toggle
and degrades gracefully when watchdog is not installed.
"""

from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from watchdog.events import FileSystemEvent, FileSystemEventHandler
    from watchdog.observers import Observer

    from snipcontext.config.settings import Config
    from snipcontext.core.search import HybridSearch
    from snipcontext.core.storage import StorageEngine

logger = logging.getLogger(__name__)


try:  # pragma: no cover - optional dependency
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer

    _WATCHDOG_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dependency
    _WATCHDOG_AVAILABLE = False
    FileSystemEventHandler = object
    Observer = None


class SnippetChangeHandler(FileSystemEventHandler):
    """React to snippet file changes by rebuilding the search index.

    Uses a debounce mechanism to avoid excessive reindexing during batch
    operations (git checkout, IDE saves, etc.). Events are collected during
    a configurable window, then a single reindex is triggered.
    """

    def __init__(
        self,
        search_engine: HybridSearch,
        storage_engine: StorageEngine,
        debounce_seconds: float = 2.0,
    ) -> None:
        self.search = search_engine
        self.storage = storage_engine
        self.debounce_seconds = debounce_seconds
        self._timer: threading.Timer | None = None
        self._lock = threading.Lock()

    def on_any_event(self, event: FileSystemEvent) -> None:
        if event.is_directory or event.src_path.endswith(".tmp"):
            return
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
            self._timer = threading.Timer(self.debounce_seconds, self._do_reindex)
            self._timer.daemon = True
            self._timer.start()

    def _do_reindex(self) -> None:
        try:
            snippets = self.storage.list_all()
        except Exception as exc:
            logger.debug("Watcher handler skipped update: %s", exc)
            return
        self.search.rebuild_incremental(snippets)
        logger.debug("Debounced reindex complete (%d snippets)", len(snippets))

    def cancel(self) -> None:
        """Cancel any pending reindex timer."""
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None


class SnippetWatcher:
    """Filesystem watcher that keeps the search index in sync with snippets."""

    def __init__(
        self,
        config: Config,
        search_engine: HybridSearch,
        storage_engine: StorageEngine,
    ) -> None:
        self.config = config
        self.search = search_engine
        self.storage = storage_engine
        self.observer: Observer | None = None
        self._handler: SnippetChangeHandler | None = None

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

        debounce = getattr(self.config, "watchdog_debounce_seconds", 2.0)
        self._handler = SnippetChangeHandler(self.search, self.storage, debounce_seconds=debounce)
        self.observer = Observer()
        assert self.observer is not None
        self.observer.schedule(self._handler, str(self.config.snippets_path), recursive=False)
        self.observer.start()
        print(f"Watching {self.config.snippets_path} for changes (debounce={debounce}s)...")
        try:
            while self.observer.is_alive():
                self.observer.join(1)
        except KeyboardInterrupt:
            self.observer.stop()
            self.observer.join()
        finally:
            if self._handler:
                self._handler.cancel()
        print("Watcher stopped.")
