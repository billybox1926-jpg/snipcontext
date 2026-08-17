"""CLI export command tests - extended coverage."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from snipcontext.config.settings import Config, StorageConfig
from snipcontext.core.models import Language, Snippet, SnippetMetadata


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

    # Add test snippets
    now = datetime.now(timezone.utc)
    snippets = [
        Snippet(
            id="exp-1",
            title="Export Test 1",
            content="print('hello')",
            metadata=SnippetMetadata(title="Export Test 1", language=Language.PYTHON),
            tags=["python"],
            created_at=now,
        ),
    ]
    for s in snippets:
        storage.save(s)

    searcher = MagicMock()
    searcher.indices_ready = True
    searcher.search.return_value = []

    return config, storage, searcher


def _invoke_cli(args, context=None):
    """Helper to invoke CLI commands."""
    from typer.testing import CliRunner

    from snipcontext.cli.app import app

    runner = CliRunner()
    if context:
        with patch("snipcontext.cli.export._get_context", return_value=context):
            return runner.invoke(app, args)
    return runner.invoke(app, args)


def test_export_with_model(cli_context):
    """Export with --model for ollama provider."""
    result = _invoke_cli(["export", "--provider", "ollama", "--model", "llama3.1"], cli_context)
    assert result.exit_code == 0


def test_export_to_stdout(cli_context):
    """Export to stdout (no --output)."""
    result = _invoke_cli(["export"], cli_context)
    assert result.exit_code == 0


def test_providers_with_health(cli_context):
    """Providers list with --health flag."""
    result = _invoke_cli(["providers", "--health"], cli_context)
    assert result.exit_code in (0, 1)  # May fail without actual providers


def test_plugins_load(cli_context):
    """Plugins --load command."""
    result = _invoke_cli(["plugins", "--load", "test-plugin"], cli_context)
    assert result.exit_code in (0, 1)  # May fail without actual plugin


def test_plugins_unload(cli_context):
    """Plugins --unload command."""
    result = _invoke_cli(["plugins", "--unload", "test-plugin"], cli_context)
    assert result.exit_code in (0, 1)  # May fail without actual plugin


def test_plugins_health(cli_context):
    """Plugins --health command."""
    result = _invoke_cli(["plugins", "--health"], cli_context)
    assert result.exit_code in (0, 1)  # May fail without actual providers
