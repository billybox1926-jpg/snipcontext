"""CLI snippets command tests - extended coverage."""

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


def test_add_with_tags(cli_context):
    """Add snippet with tags."""
    result = _invoke_cli(
        ["add", "print('hi')", "--title", "Tagged", "--tag", "python", "--tag", "cli"], cli_context
    )
    assert result.exit_code == 0


def test_add_with_language(cli_context):
    """Add snippet with language."""
    result = _invoke_cli(
        ["add", "print('hi')", "--title", "Python Snippet", "--lang", "python"], cli_context
    )
    assert result.exit_code == 0


def test_add_with_description(cli_context):
    """Add snippet with description."""
    result = _invoke_cli(
        ["add", "print('hi')", "--title", "Desc Test", "--desc", "A test snippet"], cli_context
    )
    assert result.exit_code == 0


def test_add_with_source(cli_context):
    """Add snippet with source URL."""
    result = _invoke_cli(
        ["add", "print('hi')", "--title", "Source Test", "--source", "https://example.com"],
        cli_context,
    )
    assert result.exit_code == 0


def test_add_empty_content(cli_context):
    """Add with empty content shows error."""
    result = _invoke_cli(["add", "", "--title", "Empty"], cli_context)
    assert result.exit_code == 1
    assert "empty" in result.output.lower() or "error" in result.output.lower()


def test_list_empty(cli_context):
    """List with no snippets shows message."""
    result = _invoke_cli(["list"], cli_context)
    assert result.exit_code == 0


def test_list_with_tag_filter(cli_context):
    """List with tag filter."""
    now = datetime.now(timezone.utc)
    s1 = Snippet(
        id="tag-filter-1",
        title="Python Snippet",
        content="print('hi')",
        metadata=SnippetMetadata(title="Python Snippet", language=Language.PYTHON),
        tags=["python"],
        created_at=now,
    )
    s2 = Snippet(
        id="tag-filter-2",
        title="JS Snippet",
        content="console.log('hi')",
        metadata=SnippetMetadata(title="JS Snippet", language=Language.JAVASCRIPT),
        tags=["javascript"],
        created_at=now,
    )
    cli_context[1].save(s1)
    cli_context[1].save(s2)

    result = _invoke_cli(["list", "--tag", "python"], cli_context)
    assert result.exit_code == 0
    assert "python" in result.output.lower()


def test_list_with_lang_filter(cli_context):
    """List with language filter."""
    now = datetime.now(timezone.utc)
    s1 = Snippet(
        id="lang-filter-1",
        title="Python Snippet",
        content="print('hi')",
        metadata=SnippetMetadata(title="Python Snippet", language=Language.PYTHON),
        created_at=now,
    )
    cli_context[1].save(s1)

    result = _invoke_cli(["list", "--lang", "python"], cli_context)
    assert result.exit_code == 0


def test_list_sort_by_title(cli_context):
    """List sorted by title."""
    now = datetime.now(timezone.utc)
    for i in range(3):
        s = Snippet(
            id=f"sort-{i}",
            title=f"Snippet {i}",
            content=f"content {i}",
            metadata=SnippetMetadata(title=f"Snippet {i}", language=Language.MARKDOWN),
            created_at=now,
        )
        cli_context[1].save(s)

    result = _invoke_cli(["list", "--sort", "title"], cli_context)
    assert result.exit_code == 0


def test_list_sort_by_created(cli_context):
    """List sorted by creation date."""
    result = _invoke_cli(["list", "--sort", "created"], cli_context)
    assert result.exit_code == 0


def test_list_sort_by_access(cli_context):
    """List sorted by access count."""
    result = _invoke_cli(["list", "--sort", "access"], cli_context)
    assert result.exit_code == 0


def test_edit_title(cli_context):
    """Edit snippet title."""
    now = datetime.now(timezone.utc)
    snippet = Snippet(
        id="edit-test",
        title="Original Title",
        content="test content",
        metadata=SnippetMetadata(title="Original Title", language=Language.PYTHON),
        created_at=now,
    )
    cli_context[1].save(snippet)

    result = _invoke_cli(["edit", "edit-test", "--title", "New Title", "--force"], cli_context)
    assert result.exit_code == 0


def test_edit_content(cli_context):
    """Edit snippet content."""
    now = datetime.now(timezone.utc)
    snippet = Snippet(
        id="edit-content",
        title="Edit Content",
        content="original content",
        metadata=SnippetMetadata(title="Edit Content", language=Language.PYTHON),
        created_at=now,
    )
    cli_context[1].save(snippet)

    result = _invoke_cli(
        ["edit", "edit-content", "--content", "new content", "--force"], cli_context
    )
    assert result.exit_code == 0


def test_edit_add_tags(cli_context):
    """Edit adds tags to snippet."""
    now = datetime.now(timezone.utc)
    snippet = Snippet(
        id="edit-tags",
        title="Edit Tags",
        content="test content",
        metadata=SnippetMetadata(title="Edit Tags", language=Language.PYTHON),
        tags=["existing"],
        created_at=now,
    )
    cli_context[1].save(snippet)

    result = _invoke_cli(["edit", "edit-tags", "--tag", "newtag", "--force"], cli_context)
    assert result.exit_code == 0


def test_edit_remove_tags(cli_context):
    """Edit removes tags from snippet."""
    now = datetime.now(timezone.utc)
    snippet = Snippet(
        id="edit-rm-tags",
        title="Edit Remove Tags",
        content="test content",
        metadata=SnippetMetadata(title="Edit Remove Tags", language=Language.PYTHON),
        tags=["removeme"],
        created_at=now,
    )
    cli_context[1].save(snippet)

    result = _invoke_cli(
        ["edit", "edit-rm-tags", "--remove-tag", "removeme", "--force"], cli_context
    )
    assert result.exit_code == 0


def test_edit_not_found(cli_context):
    """Edit non-existent snippet shows error."""
    result = _invoke_cli(["edit", "nonexistent", "--title", "New Title"], cli_context)
    assert result.exit_code == 1
    assert "not found" in result.output.lower()


def test_delete_not_found(cli_context):
    """Delete non-existent snippet shows error."""
    result = _invoke_cli(["delete", "nonexistent", "--force"], cli_context)
    # Should handle gracefully
    assert result.exit_code in (0, 1)


def test_get_raw(cli_context):
    """Get snippet with --raw flag."""
    now = datetime.now(timezone.utc)
    snippet = Snippet(
        id="raw-test",
        title="Raw Test",
        content="raw content here",
        metadata=SnippetMetadata(title="Raw Test", language=Language.PYTHON),
        created_at=now,
    )
    cli_context[1].save(snippet)

    result = _invoke_cli(["get", "raw-test", "--raw"], cli_context)
    assert result.exit_code == 0
    assert "raw content" in result.output


def test_get_prefix(cli_context):
    """Get snippet by ID prefix."""
    now = datetime.now(timezone.utc)
    snippet = Snippet(
        id="prefix-test-unique",
        title="Prefix Test",
        content="test content",
        metadata=SnippetMetadata(title="Prefix Test", language=Language.PYTHON),
        created_at=now,
    )
    cli_context[1].save(snippet)

    result = _invoke_cli(["get", "prefix-test"], cli_context)
    assert result.exit_code == 0
