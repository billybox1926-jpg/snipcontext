"""Tests for core/snippet_ops.py - extended coverage."""

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from snipcontext.core.models import Language, Snippet, SnippetMetadata
from snipcontext.core.snippet_ops import (
    add_snippet,
    create_snippet,
    get_snippet,
    list_snippets,
    resolve_language,
)
from snipcontext.core.storage import StorageError


def test_add_snippet():
    """add_snippet creates and saves a snippet."""
    mock_storage = MagicMock()

    result = add_snippet(
        mock_storage,
        content="print('hello')",
        title="Test",
        description="Test desc",
        language="python",
        tags=["test"],
    )

    assert result.metadata.title == "Test"
    mock_storage.save.assert_called_once()


def test_get_snippet_by_id():
    """get_snippet retrieves by exact ID."""
    mock_storage = MagicMock()
    mock_storage.get.return_value = MagicMock(spec=Snippet)

    get_snippet(mock_storage, "test-id")
    mock_storage.get.assert_called_with("test-id")


def test_get_snippet_by_prefix():
    """get_snippet retrieves by prefix when exact match fails."""
    mock_storage = MagicMock()
    mock_storage.get.side_effect = StorageError("not found", code="not_found")

    mock_snippet = MagicMock(spec=Snippet)
    mock_snippet.id = "test-123"
    mock_storage.iter_all.return_value = [mock_snippet]

    result = get_snippet(mock_storage, "test")
    assert result.id == "test-123"


def test_get_snippet_multiple_matches():
    """get_snippet raises ValueError for multiple prefix matches."""
    mock_storage = MagicMock()
    mock_storage.get.side_effect = StorageError("not found", code="not_found")

    mock_s1 = MagicMock(spec=Snippet)
    mock_s1.id = "test-123"
    mock_s2 = MagicMock(spec=Snippet)
    mock_s2.id = "test-456"
    mock_storage.iter_all.return_value = [mock_s1, mock_s2]

    with pytest.raises(ValueError, match="Multiple matches"):
        get_snippet(mock_storage, "test")


def test_get_snippet_not_found():
    """get_snippet raises StorageError when no match found."""
    mock_storage = MagicMock()
    mock_storage.get.side_effect = StorageError("not found", code="not_found")
    mock_storage.iter_all.return_value = []

    with pytest.raises(StorageError):
        get_snippet(mock_storage, "nonexistent")


def test_list_snippets_no_filters():
    """list_snippets returns all snippets."""
    now = datetime.now(timezone.utc)
    mock_storage = MagicMock()
    mock_storage.list_all.return_value = [
        Snippet(
            id="s1",
            title="Test",
            content="content",
            metadata=SnippetMetadata(title="Test", language=Language.PYTHON),
            created_at=now,
        )
    ]

    result = list_snippets(mock_storage)
    assert len(result) == 1


def test_list_snippets_with_tag():
    """list_snippets filters by tag."""
    now = datetime.now(timezone.utc)
    mock_s1 = Snippet(
        id="t1",
        title="Python",
        content="py",
        metadata=SnippetMetadata(title="Python", language=Language.PYTHON),
        tags=["python"],
        created_at=now,
    )
    mock_s2 = Snippet(
        id="t2",
        title="JS",
        content="js",
        metadata=SnippetMetadata(title="JS", language=Language.JAVASCRIPT),
        tags=["javascript"],
        created_at=now,
    )

    mock_storage = MagicMock()
    mock_storage.list_all.return_value = [mock_s1, mock_s2]

    result = list_snippets(mock_storage, tag="python")
    assert len(result) == 1
    assert result[0].metadata.title == "Python"


def test_list_snippets_with_language():
    """list_snippets filters by language."""
    now = datetime.now(timezone.utc)
    mock_s1 = Snippet(
        id="l1",
        title="Python",
        content="py",
        metadata=SnippetMetadata(title="Python", language=Language.PYTHON),
        created_at=now,
    )
    mock_s2 = Snippet(
        id="l2",
        title="JS",
        content="js",
        metadata=SnippetMetadata(title="JS", language=Language.JAVASCRIPT),
        created_at=now,
    )

    mock_storage = MagicMock()
    mock_storage.list_all.return_value = [mock_s1, mock_s2]

    result = list_snippets(mock_storage, language="python")
    assert len(result) == 1
    assert result[0].metadata.title == "Python"


def test_list_snippets_with_sort():
    """list_snippets sorts by specified field."""
    now = datetime.now(timezone.utc)
    mock_s1 = Snippet(
        id="s1",
        title="B Snippet",
        content="b",
        metadata=SnippetMetadata(title="B Snippet", language=Language.PYTHON),
        created_at=now,
    )
    mock_s2 = Snippet(
        id="s2",
        title="A Snippet",
        content="a",
        metadata=SnippetMetadata(title="A Snippet", language=Language.PYTHON),
        created_at=now,
    )

    mock_storage = MagicMock()
    mock_storage.list_all.return_value = [mock_s1, mock_s2]

    result = list_snippets(mock_storage, sort="title")
    assert result[0].metadata.title == "A Snippet"


def test_create_snippet_empty_content():
    """create_snippet raises ValueError for empty content."""
    with pytest.raises(ValueError, match="Content cannot be empty"):
        create_snippet("", "Test", "Desc", "python", [])


def test_create_snippet_invalid_language():
    """create_snippet uses UNKNOWN for invalid language."""
    snippet = create_snippet("test", "Title", "Desc", "invalid_lang", [])
    assert snippet.metadata.language == Language.UNKNOWN


def test_create_snippet_with_known_language():
    """create_snippet parses known language."""
    snippet = create_snippet("test", "Title", "Desc", "python", [])
    assert snippet.metadata.language == Language.PYTHON


def test_resolve_language_unknown_extension():
    """resolve_language returns empty for unknown extension."""
    result = resolve_language("", "file.unknownext", True, "/path/to/file.unknownext")
    assert result == ""
