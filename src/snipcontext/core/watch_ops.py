"""Watch domain business logic.

Pure functions for file watcher orchestration.
No I/O, no CLI dependencies.
"""

from __future__ import annotations

from snipcontext.config.settings import Config
from snipcontext.core.search import HybridSearch
from snipcontext.core.storage import StorageEngine
from snipcontext.core.watcher import SnippetWatcher


def create_watcher(
    config: Config,
    search: HybridSearch,
    storage: StorageEngine,
) -> SnippetWatcher:
    """Create a configured SnippetWatcher instance.

    Args:
        config: Application config.
        search: Hybrid search instance.
        storage: Storage engine instance.

    Returns:
        Configured SnippetWatcher (not yet started).
    """
    return SnippetWatcher(config, search, storage)


def is_watcher_enabled(config: Config) -> bool:
    """Check if the file watcher is enabled in config.

    Args:
        config: Application config.

    Returns:
        True if watcher is enabled.
    """
    return getattr(config, "watchdog_enabled", True)


def get_watcher_debounce(config: Config) -> float:
    """Get the debounce interval from config.

    Args:
        config: Application config.

    Returns:
        Debounce interval in seconds.
    """
    return getattr(config, "watchdog_debounce_seconds", 2.0)
