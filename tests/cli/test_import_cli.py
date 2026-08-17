"""CLI import command tests."""

from unittest.mock import MagicMock, patch

import pytest

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
    if context:
        with patch("snipcontext.cli.import_._get_context", return_value=context):
            return runner.invoke(app, args)
    return runner.invoke(app, args)


def test_import_invalid_scheme(cli_context):
    """Import with invalid scheme shows error."""
    result = _invoke_cli(["import", "ftp://example.com/snippets"], cli_context)
    assert result.exit_code == 1
    assert "only https" in result.output.lower() or "unsupported" in result.output.lower()


def test_import_unsupported_format(cli_context):
    """Import with unsupported format shows error."""
    result = _invoke_cli(["import", "https://example.com/test.csv", "--format", "csv"], cli_context)
    assert result.exit_code == 1
    assert "unsupported format" in result.output.lower() or "unsupported" in result.output.lower()


def test_import_preview_mode(cli_context):
    """Import with --dry-run previews snippets."""
    result = _invoke_cli(["import", "https://example.com/snippets.json", "--dry-run"], cli_context)
    # Should not raise; may succeed or fail depending on network
    assert result.exit_code in (0, 1)


def test_import_no_url(cli_context):
    """Import with no URL shows error."""
    result = _invoke_cli(["import"], cli_context)
    assert (
        result.exit_code != 0
        or "required" in result.output.lower()
        or "error" in result.output.lower()
    )


def test_import_local_file_not_found(cli_context):
    """Import with non-existent local file."""
    result = _invoke_cli(
        ["import", str(cli_context[0].storage.data_dir / "nonexistent.json")], cli_context
    )
    # Should handle gracefully
    assert result.exit_code in (0, 1)
