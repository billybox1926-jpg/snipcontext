"""CLI search output formatting tests - target uncovered lines."""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

from snipcontext.config.settings import Config, StorageConfig
from snipcontext.core.models import Language, Snippet, SnippetMetadata, SearchResult


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
    searcher.indices_ready = True
    
    return config, storage, searcher


def _invoke_cli(args, context=None):
    """Helper to invoke CLI commands."""
    from typer.testing import CliRunner
    from snipcontext.cli.app import app
    
    runner = CliRunner()
    if context:
        with patch("snipcontext.cli.search._get_context", return_value=context):
            return runner.invoke(app, args)
    return runner.invoke(app, args)


def test_search_with_all_options(cli_context):
    """Search with multiple options to cover output formatting."""
    _, _, mock_search = cli_context
    
    now = datetime.now(timezone.utc)
    snippet = Snippet(
        id="full-test",
        title="Full Test Snippet",
        content="def hello(): print('hello')",
        metadata=SnippetMetadata(
            title="Full Test Snippet",
            description="A comprehensive test",
            language=Language.PYTHON,
            framework="fastapi",
            version="1.0",
            source_url="https://example.com",
        ),
        tags=["python", "cli", "test"],
        created_at=now,
    )
    
    result = SearchResult(snippet=snippet, score=0.95, matched_by="keyword")
    mock_search.search.return_value = [result]
    
    result = _invoke_cli([
        "search", "python",
        "--mode", "keyword",
        "--limit", "5",
        "--threshold", "0.3",
        "--fuzzy",
        "--explain",
    ], cli_context)
    
    assert result.exit_code == 0


def test_search_with_group_by_tag(cli_context):
    """Search with --group-by tag to cover grouped output."""
    _, _, mock_search = cli_context
    
    now = datetime.now(timezone.utc)
    snippet = Snippet(
        id="tag-test",
        title="Tag Test",
        content="test content",
        metadata=SnippetMetadata(title="Tag Test", language=Language.PYTHON),
        tags=["python"],
        created_at=now,
    )
    
    result = SearchResult(snippet=snippet, score=0.9, matched_by="keyword")
    mock_search.search.return_value = [result]
    mock_search.group_results.return_value = {"python": [result]}
    
    result = _invoke_cli(["search", "python", "--group-by", "tag"], cli_context)
    assert result.exit_code == 0


def test_search_no_results_with_suggestions(cli_context):
    """Search with no results shows suggestions."""
    _, _, mock_search = cli_context
    mock_search.search.return_value = []
    
    result = _invoke_cli(["search", "xyznonexistent"], cli_context)
    assert result.exit_code == 0
    output = result.output.lower()
    assert "no results" in output or "0 results" in output


def test_search_with_hybrid_mode(cli_context):
    """Search with hybrid mode to cover hybrid path."""
    _, _, mock_search = cli_context
    
    now = datetime.now(timezone.utc)
    snippet = Snippet(
        id="hybrid-test",
        title="Hybrid Test",
        content="test content",
        metadata=SnippetMetadata(title="Hybrid Test", language=Language.PYTHON),
        created_at=now,
    )
    
    result = SearchResult(snippet=snippet, score=0.85, matched_by="hybrid")
    mock_search.search.return_value = [result]
    
    result = _invoke_cli(["search", "test", "--mode", "hybrid"], cli_context)
    assert result.exit_code == 0
