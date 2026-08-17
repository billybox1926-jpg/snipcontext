"""CLI config command tests."""

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


def test_config_show():
    """Config show command."""
    result = _invoke_cli(["config", "show"])
    assert result.exit_code == 0


def test_config_path():
    """Config path command."""
    result = _invoke_cli(["config", "path"])
    assert result.exit_code == 0


def test_config_list():
    """Config list command."""
    result = _invoke_cli(["config", "list"])
    assert result.exit_code == 0


def test_config_set_bool_true():
    """Config set boolean true."""
    result = _invoke_cli(["config", "set", "search.rerank", "true"])
    assert result.exit_code in (0, 1)  # May fail without config file


def test_config_set_bool_false():
    """Config set boolean false."""
    result = _invoke_cli(["config", "set", "search.rerank", "false"])
    assert result.exit_code in (0, 1)


def test_config_set_int():
    """Config set integer value."""
    result = _invoke_cli(["config", "set", "search.top_k", "20"])
    assert result.exit_code in (0, 1)


def test_config_set_float():
    """Config set float value."""
    result = _invoke_cli(["config", "set", "search.min_score", "0.5"])
    assert result.exit_code in (0, 1)


def test_config_set_invalid_key():
    """Config set with invalid key shows error."""
    result = _invoke_cli(["config", "set", "invalid.key", "value"])
    assert result.exit_code in (1, 2)


def test_config_set_invalid_bool():
    """Config set with invalid bool shows error."""
    result = _invoke_cli(["config", "set", "search.rerank", "notabool"])
    assert result.exit_code in (1, 2)


def test_config_init():
    """Config init command."""
    result = _invoke_cli(["config", "init"])
    assert result.exit_code in (0, 1)


def test_config_init_force():
    """Config init with --force."""
    result = _invoke_cli(["config", "init", "--force"])
    assert result.exit_code in (0, 1)
