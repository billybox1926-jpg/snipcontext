"""CLI search command tests - extended coverage."""
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
import tempfile
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


def _invoke_cli(args, context=None, input_data=None):
    """Helper to invoke CLI commands."""
    from typer.testing import CliRunner
    from snipcontext.cli.app import app
    
    runner = CliRunner()
    if context:
        with patch("snipcontext.cli.search._get_context", return_value=context):
            return runner.invoke(app, args, input=input_data)
    return runner.invoke(app, args, input=input_data)


def test_search_with_mode_keyword(cli_context):
    """Search with --mode keyword."""
    result = _invoke_cli(["search", "python", "--mode", "keyword"], cli_context)
    assert result.exit_code == 0


def test_search_with_mode_semantic(cli_context):
    """Search with --mode semantic."""
    result = _invoke_cli(["search", "python", "--mode", "semantic"], cli_context)
    assert result.exit_code == 0


def test_search_with_threshold(cli_context):
    """Search with --threshold filter."""
    result = _invoke_cli(["search", "python", "--threshold", "0.5"], cli_context)
    assert result.exit_code == 0


def test_search_with_fuzzy(cli_context):
    """Search with --fuzzy flag."""
    result = _invoke_cli(["search", "python", "--fuzzy"], cli_context)
    assert result.exit_code == 0


def test_search_with_no_semantic(cli_context):
    """Search with --no-semantic flag."""
    result = _invoke_cli(["search", "python", "--no-semantic"], cli_context)
    assert result.exit_code == 0


def test_search_with_lang_filter(cli_context):
    """Search with --lang filter."""
    result = _invoke_cli(["search", "python", "--lang", "python"], cli_context)
    assert result.exit_code == 0


def test_search_with_tag_filter(cli_context):
    """Search with --tag filter."""
    result = _invoke_cli(["search", "python", "--tag", "cli"], cli_context)
    assert result.exit_code == 0


def test_search_with_boost_recent(cli_context):
    """Search with --boost-recent flag."""
    result = _invoke_cli(["search", "python", "--boost-recent"], cli_context)
    assert result.exit_code == 0


def test_search_with_explain(cli_context):
    """Search with --explain flag."""
    result = _invoke_cli(["search", "python", "--explain"], cli_context)
    assert result.exit_code == 0


def test_search_with_group_by_language(cli_context):
    """Search with --group-by language."""
    result = _invoke_cli(["search", "python", "--group-by", "language"], cli_context)
    assert result.exit_code == 0


def test_search_with_semantic_weight(cli_context):
    """Search with --semantic-weight."""
    result = _invoke_cli(["search", "python", "--semantic-weight", "0.8"], cli_context)
    assert result.exit_code == 0


def test_search_with_keyword_weight(cli_context):
    """Search with --keyword-weight."""
    result = _invoke_cli(["search", "python", "--keyword-weight", "0.3"], cli_context)
    assert result.exit_code == 0


def test_search_multiple_queries(cli_context):
    """Search with multiple queries."""
    result = _invoke_cli(["search", "python", "cli"], cli_context)
    assert result.exit_code == 0


def test_search_with_index_flag(cli_context):
    """Search with --index flag forces reindex."""
    result = _invoke_cli(["search", "python", "--index"], cli_context)
    assert result.exit_code == 0


def test_build_index_command(cli_context):
    """Build-index command."""
    result = _invoke_cli(["build-index"], cli_context)
    assert result.exit_code == 0


def test_build_index_force(cli_context):
    """Build-index with --force."""
    result = _invoke_cli(["build-index", "--force"], cli_context)
    assert result.exit_code == 0
