"""VectorIndex tests with simplified mocking."""
import numpy as np
import pytest
from pathlib import Path
import tempfile
from unittest.mock import MagicMock, patch, PropertyMock
from datetime import datetime, timezone

from snipcontext.core.models import Language, Snippet
from snipcontext.config.settings import Config


@pytest.fixture
def mock_config():
    return Config(
        storage__data_dir=Path(tempfile.mkdtemp()),
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


def test_search_empty_index_returns_empty(mock_config):
    """Search on untrained index returns empty list."""
    with patch("snipcontext.core.indexes.vector_index.SEMANTIC_AVAILABLE", False):
        from snipcontext.core.indexes.vector_index import VectorIndex
        idx = VectorIndex(mock_config)
        assert idx.search(np.array([1.0, 0.0], dtype=np.float32), top_k=5, min_score=0.0) == []


def test_search_top_k_zero_returns_empty(mock_config):
    """Search with top_k=0 returns empty list."""
    with patch("snipcontext.core.indexes.vector_index.SEMANTIC_AVAILABLE", False):
        from snipcontext.core.indexes.vector_index import VectorIndex
        idx = VectorIndex(mock_config)
        assert idx.search(np.array([1.0, 0.0], dtype=np.float32), top_k=0, min_score=0.0) == []


def test_remove_vector_returns_gracefully(mock_config):
    """remove_vector on empty index should not crash."""
    with patch("snipcontext.core.indexes.vector_index.SEMANTIC_AVAILABLE", True):
        from snipcontext.core.indexes.vector_index import VectorIndex
        idx = VectorIndex(mock_config)
        # Should not crash even if backend is None
        idx.remove_vector("nonexistent")


def test_add_vector_raises_when_unavailable(mock_config):
    """add_vector raises ImportError when SEMANTIC_AVAILABLE is False."""
    from snipcontext.core.models import Language, Snippet
    from datetime import datetime, timezone
    
    with patch("snipcontext.core.indexes.vector_index.SEMANTIC_AVAILABLE", False):
        from snipcontext.core.indexes.vector_index import VectorIndex
        idx = VectorIndex(mock_config)
        
        now = datetime.now(timezone.utc)
        snippet = Snippet(
            id="test", title="t", content="c", 
            language=Language.MARKDOWN, tags=[], created_at=now
        )
        
        with pytest.raises(ImportError, match="FAISS"):
            idx.add_vector(snippet, None)


def test_save_no_op_when_unavailable(mock_config):
    """save() is a no-op when SEMANTIC_AVAILABLE is False."""
    with patch("snipcontext.core.indexes.vector_index.SEMANTIC_AVAILABLE", False):
        from snipcontext.core.indexes.vector_index import VectorIndex
        idx = VectorIndex(mock_config)
        # Should not crash
        idx.save(mock_config.index_path)


def test_load_returns_false_when_unavailable(mock_config):
    """load() returns False when SEMANTIC_AVAILABLE is False."""
    with patch("snipcontext.core.indexes.vector_index.SEMANTIC_AVAILABLE", False):
        from snipcontext.core.indexes.vector_index import VectorIndex
        idx = VectorIndex(mock_config)
        assert idx.load(mock_config.index_path) is False


def test_is_trained_reflects_backend_state(mock_config):
    """is_trained property reflects backend training state."""
    with patch("snipcontext.core.indexes.vector_index.SEMANTIC_AVAILABLE", False):
        from snipcontext.core.indexes.vector_index import VectorIndex
        idx = VectorIndex(mock_config)
        assert idx.is_trained is False


def test_count_reflects_backend_state(mock_config):
    """count property reflects backend vector count."""
    with patch("snipcontext.core.indexes.vector_index.SEMANTIC_AVAILABLE", False):
        from snipcontext.core.indexes.vector_index import VectorIndex
        idx = VectorIndex(mock_config)
        assert idx.count == 0
