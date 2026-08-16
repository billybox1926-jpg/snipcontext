"""Tests for watcher.py - SnippetWatcher and SnippetChangeHandler."""

import threading
import time
from pathlib import Path
import tempfile

import pytest
from unittest.mock import MagicMock, patch

from snipcontext.config.settings import Config, StorageConfig
from snipcontext.core.watcher import SnippetChangeHandler, SnippetWatcher


@pytest.fixture
def mock_config():
    tmpdir = Path(tempfile.mkdtemp())
    storage_config = StorageConfig(data_dir=tmpdir, snippets_dir="snippets", index_dir="index")
    return Config(
        storage=storage_config,
        search__top_k=10,
        search__default_mode="hybrid",
        search__min_score=0.0,
        search__semantic_weight=0.5,
        search__keyword_weight=0.5,
        embedding__model_name="all-MiniLM-L6-v2",
        embedding__device="cpu",
        embedding__batch_size=32,
        embedding__normalize=True,
        embedding__doc_instruction="",
        embedding__query_instruction="",
        max_snippets_per_export=100,
        snippets_per_page=20,
        watchdog_ready=False,
    )


def test_handler_initialization():
    """SnippetChangeHandler initializes with search, storage, and debounce."""
    search = MagicMock()
    storage = MagicMock()
    handler = SnippetChangeHandler(search, storage, debounce_seconds=1.5)
    assert handler.search is search
    assert handler.storage is storage
    assert handler.debounce_seconds == 1.5
    assert handler._timer is None


def test_handler_on_any_event_skips_directories():
    """on_any_event() skips directory events."""
    search = MagicMock()
    storage = MagicMock()
    handler = SnippetChangeHandler(search, storage, debounce_seconds=0.1)

    event = MagicMock()
    event.is_directory = True
    event.src_path = "/some/dir"

    handler.on_any_event(event)
    # Should not start a timer for directory events
    assert handler._timer is None


def test_handler_on_any_event_skips_tmp_files():
    """on_any_event() skips .tmp files."""
    search = MagicMock()
    storage = MagicMock()
    handler = SnippetChangeHandler(search, storage, debounce_seconds=0.1)

    event = MagicMock()
    event.is_directory = False
    event.src_path = "/some/file.tmp"

    handler.on_any_event(event)
    # Should not start a timer for .tmp files
    assert handler._timer is None


def test_handler_on_any_event_starts_timer():
    """on_any_event() starts a debounce timer for valid events."""
    search = MagicMock()
    storage = MagicMock()
    handler = SnippetChangeHandler(search, storage, debounce_seconds=0.1)

    event = MagicMock()
    event.is_directory = False
    event.src_path = "/some/file.py"

    handler.on_any_event(event)
    assert handler._timer is not None
    assert isinstance(handler._timer, threading.Timer)

    # Clean up
    handler.cancel()


def test_handler_cancel_stops_timer():
    """cancel() stops the pending timer."""
    search = MagicMock()
    storage = MagicMock()
    handler = SnippetChangeHandler(search, storage, debounce_seconds=10.0)

    event = MagicMock()
    event.is_directory = False
    event.src_path = "/some/file.py"

    handler.on_any_event(event)
    assert handler._timer is not None

    handler.cancel()
    assert handler._timer is None


def test_handler_do_reindex_calls_search():
    """_do_reindex() calls search.rebuild_incremental()."""
    search = MagicMock()
    storage = MagicMock()
    storage.list_all.return_value = [MagicMock(), MagicMock()]
    handler = SnippetChangeHandler(search, storage, debounce_seconds=0.1)

    handler._do_reindex()
    search.rebuild_incremental.assert_called_once()


def test_handler_do_reindex_handles_storage_error():
    """_do_reindex() handles storage errors gracefully."""
    search = MagicMock()
    storage = MagicMock()
    storage.list_all.side_effect = Exception("Storage error")
    handler = SnippetChangeHandler(search, storage, debounce_seconds=0.1)

    # Should not raise
    handler._do_reindex()
    search.rebuild_incremental.assert_not_called()


def test_watcher_initialization(mock_config):
    """SnippetWatcher initializes with config, search, and storage."""
    search = MagicMock()
    storage = MagicMock()
    watcher = SnippetWatcher(mock_config, search, storage)
    assert watcher.config is mock_config
    assert watcher.search is search
    assert watcher.storage is storage
    assert watcher.observer is None
    assert watcher._handler is None


def test_watcher_start_disabled(mock_config, capsys):
    """start() does nothing when watchdog_enabled is False."""
    mock_config.storage.watchdog_enabled = False
    search = MagicMock()
    storage = MagicMock()
    watcher = SnippetWatcher(mock_config, search, storage)

    watcher.start()
    assert watcher.observer is None

    captured = capsys.readouterr()
    assert "disabled" in captured.out.lower()


def test_watcher_start_watchdog_not_available(mock_config, capsys):
    """start() handles watchdog not being installed."""
    with patch("snipcontext.core.watcher._WATCHDOG_AVAILABLE", False):
        search = MagicMock()
        storage = MagicMock()
        watcher = SnippetWatcher(mock_config, search, storage)

        watcher.start()
        assert watcher.observer is None

        captured = capsys.readouterr()
        assert "not installed" in captured.out.lower()


def test_watcher_start_success(mock_config):
    """start() creates and starts observer when watchdog is available."""
    with patch("snipcontext.core.watcher._WATCHDOG_AVAILABLE", True):
        mock_observer = MagicMock()
        with patch("snipcontext.core.watcher.Observer", return_value=mock_observer):
            search = MagicMock()
            storage = MagicMock()
            watcher = SnippetWatcher(mock_config, search, storage)

            # We can't actually run the blocking loop, so we'll test the setup
            # by patching the observer's is_alive to return False immediately
            mock_observer.is_alive.return_value = False

            watcher.start()

            assert watcher.observer is mock_observer
            assert watcher._handler is not None
            mock_observer.schedule.assert_called_once()
            mock_observer.start.assert_called_once()
