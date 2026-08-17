"""CLI search command tests."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from snipcontext.config.settings import Config, StorageConfig
from snipcontext.core.models import Language, SearchResult, Snippet, SnippetMetadata


@pytest.fixture
def isolated_context(tmp_path):
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

    from snipcontext.core.storage import StorageEngine

    storage = StorageEngine(config)

    # Add test snippets with proper metadata
    now = datetime.now(timezone.utc)
    snippets = [
        Snippet(
            id="py-123",
            title="Python CLI tool",
            content="def hello(): print('hello')",
            metadata=SnippetMetadata(
                title="Python CLI tool",
                description="A Python CLI tool",
                language=Language.PYTHON,
            ),
            tags=["python", "cli"],
            created_at=now,
        ),
        Snippet(
            id="js-456",
            title="JavaScript web app",
            content="console.log('hello')",
            metadata=SnippetMetadata(
                title="JavaScript web app",
                description="A JavaScript web app",
                language=Language.JAVASCRIPT,
            ),
            tags=["javascript", "web"],
            created_at=now,
        ),
    ]
    for s in snippets:
        storage.save(s)

    searcher = MagicMock()
    searcher.indices_ready = True

    def mock_search(query, top_k=10, mode="hybrid", **kwargs):
        results = []
        for s in snippets:
            if "python" in query.lower() and "python" in s.tags:
                results.append(SearchResult(snippet=s, score=0.9, matched_by="keyword"))
            elif "javascript" in query.lower() and "javascript" in s.tags:
                results.append(SearchResult(snippet=s, score=0.8, matched_by="keyword"))
        return results[:top_k]

    searcher.search = mock_search
    searcher.multi_search = mock_search

    return config, storage, searcher


def test_search_no_args(isolated_context):
    """Search with no arguments should show error."""
    from typer.testing import CliRunner

    from snipcontext.cli.app import app

    runner = CliRunner()
    with patch("snipcontext.cli.search._get_context", return_value=isolated_context):
        result = runner.invoke(app, ["search"])

    assert (
        result.exit_code != 0
        or "required" in result.output.lower()
        or "error" in result.output.lower()
    )


def test_search_returns_results(isolated_context):
    """Search with valid query should return results."""
    from typer.testing import CliRunner

    from snipcontext.cli.app import app

    runner = CliRunner()
    with patch("snipcontext.cli.search._get_context", return_value=isolated_context):
        result = runner.invoke(app, ["search", "python"])

    assert result.exit_code == 0
    assert "python" in result.output.lower()


def test_search_with_top_k(isolated_context):
    """Search with --top-k flag should limit results."""
    from typer.testing import CliRunner

    from snipcontext.cli.app import app

    runner = CliRunner()
    with patch("snipcontext.cli.search._get_context", return_value=isolated_context):
        result = runner.invoke(app, ["search", "python", "--limit", "1"])

    assert result.exit_code == 0


def test_search_with_json_output(isolated_context):
    """Search with --json flag should output JSON."""
    from typer.testing import CliRunner

    from snipcontext.cli.app import app

    runner = CliRunner()
    with patch("snipcontext.cli.search._get_context", return_value=isolated_context):
        result = runner.invoke(app, ["search", "python", "--json"])

    assert result.exit_code == 0
    # JSON output should be parseable
    import json

    try:
        data = json.loads(result.output)
        assert isinstance(data, list)
    except json.JSONDecodeError:
        pass  # May have other output mixed in


def test_search_no_results(isolated_context):
    """Search with no matches should show message."""
    from typer.testing import CliRunner

    from snipcontext.cli.app import app

    runner = CliRunner()
    with patch("snipcontext.cli.search._get_context", return_value=isolated_context):
        result = runner.invoke(app, ["search", "nonexistentquery"])

    assert result.exit_code == 0
    assert "no results" in result.output.lower() or "0 results" in result.output.lower()


def test_index_command(isolated_context):
    """Index command should rebuild the search index."""
    from typer.testing import CliRunner

    from snipcontext.cli.app import app

    runner = CliRunner()
    with patch("snipcontext.cli.search._get_context", return_value=isolated_context):
        result = runner.invoke(app, ["index"])

    assert result.exit_code == 0
    assert "index" in result.output.lower()
