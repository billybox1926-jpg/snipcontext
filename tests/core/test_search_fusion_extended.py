"""Tests for core/search_fusion.py - HybridSearch edge cases."""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

from snipcontext.core.models import Language, Snippet, SnippetMetadata


def test_semantic_search_hydrate_empty_storage_error():
    """SemanticSearch._hydrate handles StorageError gracefully."""
    with patch("snipcontext.core.search_fusion.SEMANTIC_AVAILABLE", False):
        with patch.dict("sys.modules", {"faiss": MagicMock()}):
            from snipcontext.core.search_fusion import SemanticSearch
            
            mock_config = MagicMock()
            mock_config.search.top_k = 10
            mock_config.index_path = MagicMock()
            
            search = SemanticSearch(mock_config)
            
            mock_storage = MagicMock()
            from snipcontext.core.storage import StorageError
            mock_storage.get.side_effect = StorageError("Not found", code="not_found")
            
            result = search._hydrate([("id-1", 0.9)], "semantic", 10, mock_storage)
            assert result == []


def test_hybrid_search_indices_ready_loads_from_disk():
    """HybridSearch.indices_ready tries to load from disk."""
    with patch("snipcontext.core.search_fusion.SEMANTIC_AVAILABLE", False):
        with patch.dict("sys.modules", {"faiss": MagicMock()}):
            from snipcontext.core.search_fusion import HybridSearch
            
            mock_config = MagicMock()
            mock_config.search.top_k = 10
            mock_config.index_path = MagicMock()
            
            search = HybridSearch(mock_config)
            
            # Mock the keyword_index and vector_index directly
            search.keyword_index = MagicMock()
            search.keyword_index.is_trained = False
            search.vector_index = MagicMock()
            search.vector_index.is_trained = False
            
            # Mock load_indices to return True for keyword only
            search.load_indices = MagicMock(return_value=(False, True))
            
            result = search.indices_ready
            assert result is True


def test_hybrid_search_rebuild_keyword_index():
    """HybridSearch.rebuild_keyword_index clears dirty flag."""
    with patch("snipcontext.core.search_fusion.SEMANTIC_AVAILABLE", False):
        with patch.dict("sys.modules", {"faiss": MagicMock()}):
            from snipcontext.core.search_fusion import HybridSearch
            
            mock_config = MagicMock()
            mock_config.search.top_k = 10
            mock_config.index_path = MagicMock()
            
            search = HybridSearch(mock_config)
            search._keyword_dirty = True
            
            mock_snippets = [
                Snippet(
                    id="s1",
                    title="Test",
                    content="content",
                    metadata=SnippetMetadata(title="Test", language=Language.PYTHON),
                    created_at=datetime.now(timezone.utc),
                )
            ]
            
            search.rebuild_keyword_index(mock_snippets)
            assert search._keyword_dirty is False


def test_hybrid_search_add_snippet_marks_dirty():
    """HybridSearch.add_snippet marks keyword index dirty."""
    with patch("snipcontext.core.search_fusion.SEMANTIC_AVAILABLE", False):
        with patch.dict("sys.modules", {"faiss": MagicMock()}):
            from snipcontext.core.search_fusion import HybridSearch
            
            mock_config = MagicMock()
            mock_config.search.top_k = 10
            mock_config.index_path = MagicMock()
            
            search = HybridSearch(mock_config)
            search._keyword_dirty = False
            
            mock_snippet = MagicMock()
            search.add_snippet(mock_snippet)
            
            assert search._keyword_dirty is True


def test_hybrid_search_remove_snippet_marks_dirty():
    """HybridSearch.remove_snippet marks keyword index dirty."""
    with patch("snipcontext.core.search_fusion.SEMANTIC_AVAILABLE", False):
        with patch.dict("sys.modules", {"faiss": MagicMock()}):
            from snipcontext.core.search_fusion import HybridSearch
            
            mock_config = MagicMock()
            mock_config.search.top_k = 10
            mock_config.index_path = MagicMock()
            
            search = HybridSearch(mock_config)
            search._keyword_dirty = False
            
            search.remove_snippet("test-id")
            
            assert search._keyword_dirty is True


def test_hybrid_search_load_indices():
    """HybridSearch.load_indices returns loaded status."""
    with patch("snipcontext.core.search_fusion.SEMANTIC_AVAILABLE", False):
        with patch.dict("sys.modules", {"faiss": MagicMock()}):
            from snipcontext.core.search_fusion import HybridSearch
            
            mock_config = MagicMock()
            mock_config.search.top_k = 10
            mock_config.index_path = MagicMock()
            
            search = HybridSearch(mock_config)
            
            search.vector_index.load = MagicMock(return_value=True)
            search.keyword_index.load = MagicMock(return_value=True)
            
            sem_loaded, kw_loaded = search.load_indices()
            assert sem_loaded is True
            assert kw_loaded is True


def test_hybrid_search_search_mode_keyword():
    """HybridSearch.search with keyword mode."""
    with patch("snipcontext.core.search_fusion.SEMANTIC_AVAILABLE", False):
        with patch.dict("sys.modules", {"faiss": MagicMock()}):
            from snipcontext.core.search_fusion import HybridSearch
            
            mock_config = MagicMock()
            mock_config.search.top_k = 10
            mock_config.search.default_mode = "keyword"
            mock_config.search.min_score = 0.0
            mock_config.index_path = MagicMock()
            
            search = HybridSearch(mock_config)
            
            # Mock keyword_index entirely
            search.keyword_index = MagicMock()
            search.keyword_index.is_trained = True
            search.keyword_index.search = MagicMock(return_value=[("test-id", 0.9)])
            
            search._keyword_dirty = False
            
            mock_snippet = MagicMock()
            
            # Patch StorageEngine directly in the module
            with patch("snipcontext.core.search_fusion.StorageEngine") as mock_storage_cls:
                mock_storage = MagicMock()
                mock_storage.get.return_value = mock_snippet
                mock_storage_cls.return_value = mock_storage
                
                result = search.search("test", mode="keyword")
                # Should return results or empty list
                assert isinstance(result, list)
