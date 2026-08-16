"""CLI export command tests."""
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
import tempfile
from datetime import datetime, timezone

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
        Snippet(
            id="exp-2",
            title="Export Test 2",
            content="console.log('hello')",
            metadata=SnippetMetadata(title="Export Test 2", language=Language.JAVASCRIPT),
            tags=["javascript"],
            created_at=now,
        ),
    ]
    for s in snippets:
        storage.save(s)
    
    searcher = MagicMock()
    searcher.indices_ready = True
    searcher.search.return_value = []
    
    return config, storage, searcher


def _invoke_cli(args, context, input_data=None):
    """Helper to invoke CLI commands with mocked context."""
    from typer.testing import CliRunner
    from snipcontext.cli.app import app
    
    runner = CliRunner()
    with patch("snipcontext.cli.export._get_context", return_value=context):
        return runner.invoke(app, args, input=input_data)


def test_providers_list(cli_context):
    """List available export providers."""
    result = _invoke_cli(["providers"], cli_context)
    assert result.exit_code == 0
    assert "generic" in result.output.lower() or "provider" in result.output.lower()


def test_export_all(cli_context):
    """Export all snippets."""
    result = _invoke_cli(["export"], cli_context)
    assert result.exit_code == 0


def test_export_with_query(cli_context):
    """Export with a query filter."""
    result = _invoke_cli(["export", "--query", "python"], cli_context)
    assert result.exit_code == 0


def test_export_with_ids(cli_context):
    """Export specific snippet IDs."""
    result = _invoke_cli(["export", "--id", "exp-1"], cli_context)
    assert result.exit_code == 0


def test_export_to_file(cli_context):
    """Export to a file."""
    output_file = cli_context[0].storage.data_dir / "output.txt"
    result = _invoke_cli(["export", "--output", str(output_file)], cli_context)
    assert result.exit_code == 0
    assert output_file.exists()


def test_export_unknown_provider(cli_context):
    """Export with unknown provider shows error."""
    result = _invoke_cli(["export", "--provider", "nonexistent"], cli_context)
    assert result.exit_code == 1
    assert "unknown" in result.output.lower() or "error" in result.output.lower()


def test_plugins_list(cli_context):
    """List plugins command."""
    result = _invoke_cli(["plugins", "--list"], cli_context)
    assert result.exit_code == 0
