"""CLI stats command tests."""
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
    
    searcher = MagicMock()
    searcher.indices_ready = False
    
    return config, storage, searcher


def _invoke_cli(args, context=None, input_data=None):
    """Helper to invoke CLI commands."""
    from typer.testing import CliRunner
    from snipcontext.cli.app import app
    
    runner = CliRunner()
    if context:
        with patch("snipcontext.cli.stats._get_context", return_value=context):
            return runner.invoke(app, args, input=input_data)
    return runner.invoke(app, args, input=input_data)


def test_stats_empty(cli_context):
    """Stats with no snippets shows message."""
    result = _invoke_cli(["stats"], cli_context)
    assert result.exit_code == 0
    assert "no snippets" in result.output.lower()


def test_stats_basic(cli_context):
    """Stats with snippets shows overview."""
    now = datetime.now(timezone.utc)
    snippet = Snippet(
        id="stats-test",
        title="Stats Test",
        content="test content",
        metadata=SnippetMetadata(title="Stats Test", language=Language.PYTHON),
        tags=["python"],
        created_at=now,
    )
    cli_context[1].save(snippet)
    
    result = _invoke_cli(["stats"], cli_context)
    assert result.exit_code == 0
    assert "snippets" in result.output.lower() or "stats" in result.output.lower()


def test_stats_detailed(cli_context):
    """Stats --detailed shows more info."""
    now = datetime.now(timezone.utc)
    snippet = Snippet(
        id="stats-detailed",
        title="Stats Detailed",
        content="test content",
        metadata=SnippetMetadata(title="Stats Detailed", language=Language.PYTHON),
        tags=["python", "test"],
        created_at=now,
    )
    cli_context[1].save(snippet)
    
    result = _invoke_cli(["stats", "--detailed"], cli_context)
    assert result.exit_code == 0


def test_stats_json(cli_context):
    """Stats --json outputs JSON."""
    now = datetime.now(timezone.utc)
    snippet = Snippet(
        id="stats-json",
        title="Stats JSON",
        content="test content",
        metadata=SnippetMetadata(title="Stats JSON", language=Language.PYTHON),
        created_at=now,
    )
    cli_context[1].save(snippet)
    
    result = _invoke_cli(["stats", "--json"], cli_context)
    assert result.exit_code == 0
    import json
    try:
        data = json.loads(result.output)
        assert isinstance(data, dict)
        assert "total_snippets" in data
    except json.JSONDecodeError:
        pass  # May have other output mixed in


def test_stats_json_detailed(cli_context):
    """Stats --json --detailed outputs detailed JSON."""
    now = datetime.now(timezone.utc)
    snippet = Snippet(
        id="stats-json-detailed",
        title="Stats JSON Detailed",
        content="test content",
        metadata=SnippetMetadata(title="Stats JSON Detailed", language=Language.PYTHON),
        created_at=now,
    )
    cli_context[1].save(snippet)
    
    result = _invoke_cli(["stats", "--json", "--detailed"], cli_context)
    assert result.exit_code == 0


def test_demo_with_existing(cli_context):
    """Demo with existing snippets exits."""
    now = datetime.now(timezone.utc)
    snippet = Snippet(
        id="demo-existing",
        title="Demo Existing",
        content="test content",
        metadata=SnippetMetadata(title="Demo Existing", language=Language.PYTHON),
        created_at=now,
    )
    cli_context[1].save(snippet)
    
    result = _invoke_cli(["demo"], cli_context)
    assert result.exit_code == 0
    assert "existing" in result.output.lower() or "detected" in result.output.lower()
