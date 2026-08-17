"""CLI snippets command tests - additional edge cases."""

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
        with patch("snipcontext.cli.snippets._get_context", return_value=context):
            return runner.invoke(app, args, input=input_data)
    return runner.invoke(app, args, input=input_data)


def test_add_with_custom_metadata(cli_context):
    """Add snippet with custom metadata."""
    result = _invoke_cli(
        ["add", "print('hi')", "--title", "Custom", "--custom", "author=test"], cli_context
    )
    assert result.exit_code == 0


def test_add_with_framework(cli_context):
    """Add snippet with framework."""
    result = _invoke_cli(
        ["add", "print('hi')", "--title", "FastAPI", "--framework", "fastapi"], cli_context
    )
    assert result.exit_code == 0


def test_add_with_version(cli_context):
    """Add snippet with version."""
    result = _invoke_cli(
        ["add", "print('hi')", "--title", "Version", "--version", "1.0"], cli_context
    )
    assert result.exit_code == 0


def test_edit_with_description(cli_context):
    """Edit snippet description."""
    now = datetime.now(timezone.utc)
    snippet = Snippet(
        id="edit-desc",
        title="Edit Desc",
        content="test content",
        metadata=SnippetMetadata(title="Edit Desc", language=Language.PYTHON),
        created_at=now,
    )
    cli_context[1].save(snippet)

    result = _invoke_cli(["edit", "edit-desc", "--desc", "New description", "--force"], cli_context)
    assert result.exit_code == 0


def test_edit_with_language(cli_context):
    """Edit snippet language."""
    now = datetime.now(timezone.utc)
    snippet = Snippet(
        id="edit-lang",
        title="Edit Lang",
        content="test content",
        metadata=SnippetMetadata(title="Edit Lang", language=Language.PYTHON),
        created_at=now,
    )
    cli_context[1].save(snippet)

    result = _invoke_cli(["edit", "edit-lang", "--lang", "javascript", "--force"], cli_context)
    assert result.exit_code == 0


def test_edit_with_custom(cli_context):
    """Edit snippet custom metadata."""
    now = datetime.now(timezone.utc)
    snippet = Snippet(
        id="edit-custom",
        title="Edit Custom",
        content="test content",
        metadata=SnippetMetadata(title="Edit Custom", language=Language.PYTHON),
        created_at=now,
    )
    cli_context[1].save(snippet)

    result = _invoke_cli(["edit", "edit-custom", "--custom", "author=test", "--force"], cli_context)
    assert result.exit_code == 0


def test_list_sort_updated(cli_context):
    """List sorted by updated date."""
    result = _invoke_cli(["list", "--sort", "updated"], cli_context)
    assert result.exit_code == 0
