"""CLI history command tests."""
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
import tempfile

from snipcontext.config.settings import Config, StorageConfig


@pytest.fixture
def cli_context(tmp_path):
    """Create an isolated CLI context with temp storage."""
    storage_config = StorageConfig(data_dir=tmp_path, snippets_dir="snippets", index_dir="index")
    config = Config(
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
    config.auto_tag.enabled = False
    config.dedup.enabled = False
    
    from snipcontext.core.storage import StorageEngine
    storage = StorageEngine(config)
    
    searcher = MagicMock()
    searcher.indices_ready = False
    
    return config, storage, searcher


def _invoke_cli(args, context=None):
    """Helper to invoke CLI commands."""
    from typer.testing import CliRunner
    from snipcontext.cli.app import app
    
    runner = CliRunner()
    return runner.invoke(app, args)


def test_history_list_empty():
    """History list with no entries."""
    result = _invoke_cli(["history", "list"])
    assert result.exit_code == 0


def test_history_list_with_limit():
    """History list with custom limit."""
    result = _invoke_cli(["history", "list", "--limit", "5"])
    assert result.exit_code == 0


def test_history_favorites_empty():
    """History favorites with no entries."""
    result = _invoke_cli(["history", "favorites"])
    assert result.exit_code == 0


def test_history_add():
    """Add entry to history."""
    result = _invoke_cli(["history", "add", "test query"])
    assert result.exit_code == 0


def test_history_add_favorite():
    """Add entry to history as favorite."""
    result = _invoke_cli(["history", "add", "favorite query", "--favorite"])
    assert result.exit_code == 0


def test_history_clear_force():
    """Clear history with --force."""
    result = _invoke_cli(["history", "clear", "--force"])
    assert result.exit_code == 0


def test_history_favorite_not_found():
    """Toggle favorite on non-existent entry."""
    result = _invoke_cli(["history", "favorite", "999"])
    assert result.exit_code == 1
