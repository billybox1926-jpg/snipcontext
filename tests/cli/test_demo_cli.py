"""CLI stats demo mode tests."""
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
    
    return config, storage


def _invoke_cli(args):
    """Helper to invoke CLI commands."""
    from typer.testing import CliRunner
    from snipcontext.cli.app import app
    
    runner = CliRunner()
    return runner.invoke(app, args)


def test_stats_demo_empty_collection(cli_context):
    """Demo mode with empty collection seeds samples."""
    result = _invoke_cli(["demo"])
    assert result.exit_code == 0
    # Should seed sample snippets
    assert "sample" in result.output.lower() or "snippet" in result.output.lower()


def test_stats_demo_with_existing(cli_context):
    """Demo mode with existing snippets exits."""
    # Add a snippet first
    from datetime import datetime, timezone
    from snipcontext.core.models import Language, Snippet, SnippetMetadata
    
    now = datetime.now(timezone.utc)
    snippet = Snippet(
        id="demo-existing",
        title="Demo Existing",
        content="test content",
        metadata=SnippetMetadata(title="Demo Existing", language=Language.PYTHON),
        created_at=now,
    )
    cli_context[1].save(snippet)
    
    result = _invoke_cli(["demo"])
    assert result.exit_code == 0
    assert "existing" in result.output.lower() or "detected" in result.output.lower()
