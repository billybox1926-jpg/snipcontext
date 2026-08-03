"""Shared context for CLI commands.

Provides singleton instances of Config, StorageEngine, and HybridSearch
that are initialized once and reused across all commands.

This eliminates the pattern of calling get_config() and instantiating
StorageEngine/HybridSearch in every command function.

Usage:
    from snipcontext.cli.context import get_context
    config, storage, search = get_context()
"""

from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from snipcontext.config.settings import Config
    from snipcontext.core.search import HybridSearch
    from snipcontext.core.storage import StorageEngine

logger = logging.getLogger(__name__)

# Module-level singleton instances (initialized lazily)
_config: Config | None = None
_storage: StorageEngine | None = None
_search: HybridSearch | None = None
_lock = threading.Lock()


def get_context() -> tuple[Config, StorageEngine, HybridSearch]:
    """Get or initialize the shared CLI context.

    Thread-safe singleton initialization.
    Returns a tuple of (config, storage, search_engine).
    All three are initialized on first call and reused on subsequent calls.

    Returns:
        Tuple of (Config, StorageEngine, HybridSearch) instances.
    """
    global _config, _storage, _search

    # Fast path: already initialized
    if _config is not None and _storage is not None and _search is not None:
        return _config, _storage, _search

    # Slow path: initialize with lock
    with _lock:
        # Double-check after acquiring lock
        if _config is None:
            from snipcontext.config.settings import get_config

            _config = get_config()
            logger.debug("Initialized shared Config instance")

        if _storage is None:
            from snipcontext.core.storage import StorageEngine

            _storage = StorageEngine(_config)
            logger.debug("Initialized shared StorageEngine instance")

        if _search is None:
            from snipcontext.core.search import HybridSearch

            _search = HybridSearch(_config)
            logger.debug("Initialized shared HybridSearch instance")

    return _config, _storage, _search


def reset_context() -> None:
    """Reset all shared context instances.

    Primarily used for testing to ensure clean state between tests.
    Thread-safe.
    """
    global _config, _storage, _search
    with _lock:
        _config = None
        _storage = None
        _search = None
        _clear_config_cache()
        logger.debug("Reset shared context instances")


def _clear_config_cache() -> None:
    """Clear the settings cache so Config re-reads environment variables."""
    from snipcontext.config.settings import get_config as _get_config

    try:
        _get_config.cache_clear()
    except Exception:
        pass
