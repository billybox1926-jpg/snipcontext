"""CLI snippets command tests."""
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
    # Disable auto-tag and dedup to avoid embedding-related errors
    config.auto_tag.enabled = False
    config.dedup.enabled = False
    
    from snipcontext.core.storage import StorageEngine
    storage = StorageEngine(config)
    
    searcher = MagicMock()
    searcher.indices_ready = False
    
    return config, storage, searcher


def _invoke_cli(args, context, input_data=None):
    """Helper to invoke CLI commands with mocked context."""
    from typer.testing import CliRunner
    from snipcontext.cli.app import app
    
    runner = CliRunner()
    # Patch _get_context in each CLI module's namespace
    with patch("snipcontext.cli.snippets._get_context", return_value=context), \
         patch("snipcontext.cli.search._get_context", return_value=context):
        return runner.invoke(app, args, input=input_data)


def test_add_snippet(cli_context):
    """Add a snippet via CLI."""
    result = _invoke_cli(["add", "print('hello')", "--title", "Test", "--lang", "python"], cli_context)
    assert result.exit_code == 0
    assert "added" in result.output.lower() or "test" in result.output.lower()


def test_add_snippet_no_content(cli_context):
    """Add with no content shows error."""
    result = _invoke_cli(["add"], cli_context, input_data=None)
    assert result.exit_code == 1
    assert "no content" in result.output.lower() or "error" in result.output.lower()


def test_list_snippets(cli_context):
    """List snippets command."""
    # Add a snippet first
    now = datetime.now(timezone.utc)
    snippet = Snippet(
        id="list-test",
        title="List Test",
        content="test content",
        metadata=SnippetMetadata(title="List Test", language=Language.PYTHON),
        created_at=now,
    )
    cli_context[1].save(snippet)
    
    result = _invoke_cli(["list"], cli_context)
    assert result.exit_code == 0
    assert "list test" in result.output.lower() or "snippets" in result.output.lower()


def test_get_snippet(cli_context):
    """Get snippet by ID."""
    # Add a snippet first
    now = datetime.now(timezone.utc)
    snippet = Snippet(
        id="get-test",
        title="Get Test",
        content="test content",
        metadata=SnippetMetadata(title="Get Test", language=Language.PYTHON),
        created_at=now,
    )
    cli_context[1].save(snippet)
    
    result = _invoke_cli(["get", "get-test"], cli_context)
    assert result.exit_code == 0
    assert "get test" in result.output.lower()


def test_get_snippet_not_found(cli_context):
    """Get non-existent snippet shows error."""
    result = _invoke_cli(["get", "nonexistent"], cli_context)
    assert result.exit_code == 1
    assert "not found" in result.output.lower()


def test_delete_snippet(cli_context):
    """Delete snippet by ID."""
    # Add a snippet first
    now = datetime.now(timezone.utc)
    snippet = Snippet(
        id="del-test",
        title="Delete Test",
        content="test content",
        metadata=SnippetMetadata(title="Delete Test", language=Language.PYTHON),
        created_at=now,
    )
    cli_context[1].save(snippet)
    
    result = _invoke_cli(["delete", "del-test", "--force"], cli_context)
    assert result.exit_code == 0
