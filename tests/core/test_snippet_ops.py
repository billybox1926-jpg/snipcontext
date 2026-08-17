"""Tests for core/snippet_ops.py."""

from snipcontext.core.snippet_ops import (
    EXT_LANG_MAP,
    auto_title,
    create_snippet,
    resolve_language,
)


def test_resolve_language_explicit():
    """resolve_language returns explicit language."""
    result = resolve_language("python", "test", False, "")
    assert result == "python"


def test_resolve_language_from_file():
    """resolve_language infers from file extension."""
    result = resolve_language("", "test", True, "/path/to/file.py")
    assert result == "python"


def test_resolve_language_from_title():
    """resolve_language infers from title extension."""
    result = resolve_language("", "test.py", False, "")
    assert result == "python"


def test_resolve_language_empty():
    """resolve_language returns empty for unknown."""
    result = resolve_language("", "test", False, "")
    assert result == ""


def test_auto_title_with_content():
    """auto_title generates from first line."""
    result = auto_title("def hello():\n    pass")
    assert result == "def hello():"


def test_auto_title_long_line():
    """auto_title truncates to 50 chars."""
    long_line = "a" * 100
    result = auto_title(long_line)
    assert len(result) == 50


def test_auto_title_empty():
    """auto_title returns Untitled for empty content."""
    result = auto_title("")
    assert result == "Untitled Snippet"


def test_create_snippet():
    """create_snippet creates a valid Snippet."""
    snippet = create_snippet(
        content="print('hello')",
        title="Test",
        description="A test",
        language="python",
        tags=["test"],
    )
    assert snippet.metadata.title == "Test"
    assert snippet.content == "print('hello')"
    assert snippet.metadata.description == "A test"


def test_ext_lang_map():
    """EXT_LANG_MAP contains expected mappings."""
    assert EXT_LANG_MAP["py"] == "python"
    assert EXT_LANG_MAP["js"] == "javascript"
    assert EXT_LANG_MAP["ts"] == "typescript"
    assert EXT_LANG_MAP["md"] == "markdown"
