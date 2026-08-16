"""Test CLI search output formatting internals."""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

from snipcontext.core.models import Language, Snippet, SnippetMetadata, SearchResult


def test_print_snippet():
    """_print_snippet formats snippet output."""
    from snipcontext.cli.snippets import _print_snippet
    
    now = datetime.now(timezone.utc)
    snippet = Snippet(
        id="print-test",
        title="Print Test",
        content="print('hello')",
        metadata=SnippetMetadata(
            title="Print Test",
            description="A test snippet",
            language=Language.PYTHON,
        ),
        tags=["python"],
        created_at=now,
    )
    
    # Should not raise
    _print_snippet(snippet)


def test_print_snippet_with_score():
    """_print_snippet shows score when provided."""
    from snipcontext.cli.snippets import _print_snippet
    
    now = datetime.now(timezone.utc)
    snippet = Snippet(
        id="score-test",
        title="Score Test",
        content="test content",
        metadata=SnippetMetadata(title="Score Test", language=Language.PYTHON),
        created_at=now,
    )
    
    _print_snippet(snippet, score=0.95)


def test_print_snippet_with_index():
    """_print_snippet shows index when provided."""
    from snipcontext.cli.snippets import _print_snippet
    
    now = datetime.now(timezone.utc)
    snippet = Snippet(
        id="idx-test",
        title="Index Test",
        content="test content",
        metadata=SnippetMetadata(title="Index Test", language=Language.PYTHON),
        created_at=now,
    )
    
    _print_snippet(snippet, idx=1)


def test_search_result_id():
    """SearchResult.id property returns snippet ID."""
    now = datetime.now(timezone.utc)
    snippet = Snippet(
        id="result-id-test",
        title="Result Test",
        content="test",
        metadata=SnippetMetadata(title="Result Test", language=Language.PYTHON),
        created_at=now,
    )
    result = SearchResult(snippet=snippet, score=0.9, matched_by="keyword")
    assert result.id == "result-id-test"
