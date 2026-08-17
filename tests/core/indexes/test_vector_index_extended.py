"""Tests for core/vector_index.py - edge cases."""

from unittest.mock import MagicMock, patch

import pytest


@patch("snipcontext.core.indexes.vector_index.SEMANTIC_AVAILABLE", False)
def test_vector_index_no_semantic_backend_name():
    """VectorIndex without semantic deps has 'none' backend."""
    with patch.dict("sys.modules", {"faiss": MagicMock()}):
        from snipcontext.core.indexes.vector_index import VectorIndex

        mock_config = MagicMock()
        mock_config.index_path = MagicMock()

        idx = VectorIndex(mock_config)
        assert idx.backend_name == "none"


@patch("snipcontext.core.indexes.vector_index.SEMANTIC_AVAILABLE", False)
def test_vector_index_build_raises_import_error():
    """VectorIndex.build() raises ImportError without semantic deps."""
    with patch.dict("sys.modules", {"faiss": MagicMock()}):
        from snipcontext.core.indexes.vector_index import VectorIndex

        mock_config = MagicMock()
        mock_config.index_path = MagicMock()

        idx = VectorIndex(mock_config)

        with pytest.raises(ImportError):
            idx.build([MagicMock()], MagicMock())


@patch("snipcontext.core.indexes.vector_index.SEMANTIC_AVAILABLE", False)
def test_vector_index_add_vector_raises_import_error():
    """VectorIndex.add_vector() raises ImportError without semantic deps."""
    with patch.dict("sys.modules", {"faiss": MagicMock()}):
        from snipcontext.core.indexes.vector_index import VectorIndex

        mock_config = MagicMock()
        mock_config.index_path = MagicMock()

        idx = VectorIndex(mock_config)

        with pytest.raises(ImportError):
            idx.add_vector(MagicMock())


@patch("snipcontext.core.indexes.vector_index.SEMANTIC_AVAILABLE", False)
def test_vector_index_remove_vector_no_semantic():
    """VectorIndex.remove_vector() is a no-op without semantic deps."""
    with patch.dict("sys.modules", {"faiss": MagicMock()}):
        from snipcontext.core.indexes.vector_index import VectorIndex

        mock_config = MagicMock()
        mock_config.index_path = MagicMock()

        idx = VectorIndex(mock_config)
        # Should not raise
        idx.remove_vector("test-id")


@patch("snipcontext.core.indexes.vector_index.SEMANTIC_AVAILABLE", False)
def test_vector_index_is_trained_false():
    """VectorIndex.is_trained returns False when no backend."""
    with patch.dict("sys.modules", {"faiss": MagicMock()}):
        from snipcontext.core.indexes.vector_index import VectorIndex

        mock_config = MagicMock()
        mock_config.index_path = MagicMock()

        idx = VectorIndex(mock_config)
        assert idx.is_trained is False


@patch("snipcontext.core.indexes.vector_index.SEMANTIC_AVAILABLE", False)
def test_vector_index_count_zero():
    """VectorIndex.count returns 0 when no backend."""
    with patch.dict("sys.modules", {"faiss": MagicMock()}):
        from snipcontext.core.indexes.vector_index import VectorIndex

        mock_config = MagicMock()
        mock_config.index_path = MagicMock()

        idx = VectorIndex(mock_config)
        assert idx.count == 0


@patch("snipcontext.core.indexes.vector_index.SEMANTIC_AVAILABLE", False)
def test_vector_index_snippet_ids_empty():
    """VectorIndex.snippet_ids returns empty tuple when no backend."""
    with patch.dict("sys.modules", {"faiss": MagicMock()}):
        from snipcontext.core.indexes.vector_index import VectorIndex

        mock_config = MagicMock()
        mock_config.index_path = MagicMock()

        idx = VectorIndex(mock_config)
        assert idx.snippet_ids == ()
