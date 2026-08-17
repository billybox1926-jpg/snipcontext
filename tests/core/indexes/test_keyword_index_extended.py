"""Tests for core/indexes/keyword_index.py - edge cases."""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone
from pathlib import Path
import tempfile

from snipcontext.core.indexes.keyword_index import KeywordIndex
from snipcontext.core.models import Language, Snippet, SnippetMetadata


def test_keyword_index_build_empty():
    """KeywordIndex.build() with empty snippets."""
    mock_config = MagicMock()
    idx = KeywordIndex(mock_config)
    idx.build([])
    assert idx.is_trained is False


def test_keyword_index_search_not_trained():
    """KeywordIndex.search() returns empty when not trained."""
    mock_config = MagicMock()
    idx = KeywordIndex(mock_config)
    result = idx.search("test", top_k=5)
    assert result == []


def test_keyword_index_is_trained_false():
    """KeywordIndex.is_trained returns False when no corpus."""
    mock_config = MagicMock()
    idx = KeywordIndex(mock_config)
    assert idx.is_trained is False


def test_keyword_index_tokenize():
    """KeywordIndex._tokenize() splits on non-alphanumeric."""
    mock_config = MagicMock()
    idx = KeywordIndex(mock_config)
    
    result = idx._tokenize("hello world! test")
    assert "hello" in result
    assert "world" in result
    assert "test" in result


def test_keyword_index_tokenize_empty():
    """KeywordIndex._tokenize() handles empty string."""
    mock_config = MagicMock()
    idx = KeywordIndex(mock_config)
    
    result = idx._tokenize("")
    assert result == []


def test_keyword_index_search_with_fuzzy():
    """KeywordIndex.search() with fuzzy=True."""
    mock_config = MagicMock()
    idx = KeywordIndex(mock_config)
    
    # Manually set up a minimal index
    idx._corpus = [["python", "code"], ["javascript", "web"]]
    idx._id_map = ["id-1", "id-2"]
    idx._texts = ["python code", "javascript web"]
    idx._bm25 = None  # Force fallback scoring
    
    result = idx.search("python", top_k=5, fuzzy=True)
    assert isinstance(result, list)


def test_keyword_index_save_and_load():
    """KeywordIndex save/load roundtrip."""
    mock_config = MagicMock()
    idx = KeywordIndex(mock_config)
    
    # Build a minimal index
    idx._corpus = [["python", "code"], ["javascript", "web"]]
    idx._id_map = ["id-1", "id-2"]
    idx._texts = ["python code", "javascript web"]
    idx._bm25 = None
    
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "index.pkl"
        idx.save(path)
        
        # Load into a new index
        idx2 = KeywordIndex(mock_config)
        result = idx2.load(path)
        assert result is True
        assert idx2.is_trained is True
