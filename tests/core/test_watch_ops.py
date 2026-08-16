"""Tests for watch_ops.py business logic functions."""
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
import tempfile

from snipcontext.config.settings import Config, StorageConfig
from snipcontext.core import watch_ops


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


def test_is_watcher_enabled_returns_true_by_default(mock_config):
    """is_watcher_enabled() returns True when config.watchdog_enabled is True."""
    assert watch_ops.is_watcher_enabled(mock_config) is True


def test_is_watcher_enabled_returns_false_when_disabled(mock_config):
    """is_watcher_enabled() returns False when config.watchdog_enabled is False."""
    mock_config.storage.watchdog_enabled = False
    assert watch_ops.is_watcher_enabled(mock_config) is False


def test_get_watcher_debounce_returns_default(mock_config):
    """get_watcher_debounce() returns default value."""
    result = watch_ops.get_watcher_debounce(mock_config)
    assert result == 2.0


def test_get_watcher_debounce_returns_config_value(mock_config):
    """get_watcher_debounce() returns the configured debounce value."""
    mock_config.storage.watchdog_debounce_seconds = 5.0
    result = watch_ops.get_watcher_debounce(mock_config)
    assert result == 5.0


def test_create_watcher_returns_snippet_watcher(mock_config):
    """create_watcher() returns a SnippetWatcher instance."""
    search = MagicMock()
    storage = MagicMock()
    watcher = watch_ops.create_watcher(mock_config, search, storage)
    assert watcher is not None
    # Verify it's the right type
    from snipcontext.core.watcher import SnippetWatcher
    assert isinstance(watcher, SnippetWatcher)
