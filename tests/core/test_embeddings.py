"""EmbeddingEngine tests with proper mocking."""
import numpy as np
import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from pathlib import Path
import tempfile

from snipcontext.config.settings import Config
from snipcontext.core.models import Language, Snippet


@pytest.fixture
def mock_config():
    """Provide a Config with isolated temp storage."""
    with patch("snipcontext.config.paths.get_storage_root") as mock_root:
        mock_root.return_value = Path(tempfile.mkdtemp())
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


def test_engine_initialization(mock_config):
    """EmbeddingEngine initializes with config values."""
    with patch("snipcontext.core.embeddings.SEMANTIC_AVAILABLE", True):
        from snipcontext.core.embeddings import EmbeddingEngine
        engine = EmbeddingEngine(mock_config)
        assert engine._config is not None
        assert engine._model is None
        assert engine._model_name == "all-MiniLM-L6-v2"


def test_model_lazy_loads_on_first_access(mock_config):
    """Model is lazily loaded only when first accessed."""
    with patch("snipcontext.core.embeddings.SEMANTIC_AVAILABLE", True):
        from snipcontext.core.embeddings import EmbeddingEngine
        engine = EmbeddingEngine(mock_config)
        assert engine._model is None
        
        # Mock the model property to return a mock model
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        with patch.object(EmbeddingEngine, "model", new_callable=PropertyMock, return_value=mock_model):
            _ = engine.model


def test_model_raises_import_when_unavailable(mock_config):
    """Accessing model raises ImportError when deps unavailable."""
    with patch("snipcontext.core.embeddings.SEMANTIC_AVAILABLE", False):
        from snipcontext.core.embeddings import EmbeddingEngine
        engine = EmbeddingEngine(mock_config)
        with pytest.raises(ImportError, match="sentence-transformers"):
            _ = engine.model


def test_dimension_returns_integer(mock_config):
    """dimension property returns integer dimension."""
    with patch("snipcontext.core.embeddings.SEMANTIC_AVAILABLE", True):
        from snipcontext.core.embeddings import EmbeddingEngine
        engine = EmbeddingEngine(mock_config)
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        with patch.object(EmbeddingEngine, "model", new_callable=PropertyMock, return_value=mock_model):
            assert engine.dimension == 384


def test_dimension_raises_on_none(mock_config):
    """dimension raises RuntimeError when model returns None."""
    with patch("snipcontext.core.embeddings.SEMANTIC_AVAILABLE", True):
        from snipcontext.core.embeddings import EmbeddingEngine
        engine = EmbeddingEngine(mock_config)
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = None
        with patch.object(EmbeddingEngine, "model", new_callable=PropertyMock, return_value=mock_model):
            with pytest.raises(RuntimeError, match="no dimension"):
                _ = engine.dimension


def test_encode_empty_list_returns_empty_array(mock_config):
    """encode([]) returns empty array with correct shape."""
    with patch("snipcontext.core.embeddings.SEMANTIC_AVAILABLE", True):
        from snipcontext.core.embeddings import EmbeddingEngine
        engine = EmbeddingEngine(mock_config)
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        with patch.object(EmbeddingEngine, "model", new_callable=PropertyMock, return_value=mock_model):
            result = engine.encode([])
            assert isinstance(result, np.ndarray)
            assert result.shape == (0, 384)


def test_encode_returns_numpy_array(mock_config):
    """encode() returns numpy array with correct shape."""
    with patch("snipcontext.core.embeddings.SEMANTIC_AVAILABLE", True):
        from snipcontext.core.embeddings import EmbeddingEngine
        engine = EmbeddingEngine(mock_config)
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        mock_model.encode.return_value = np.array([[0.0] * 384] * 3, dtype=np.float32)
        with patch.object(EmbeddingEngine, "model", new_callable=PropertyMock, return_value=mock_model):
            result = engine.encode(["a", "b", "c"])
            assert isinstance(result, np.ndarray)
            assert result.shape == (3, 384)


def test_encode_query_returns_2d_array(mock_config):
    """encode_query() returns 2D array with shape (1, dimension)."""
    with patch("snipcontext.core.embeddings.SEMANTIC_AVAILABLE", True):
        from snipcontext.core.embeddings import EmbeddingEngine
        engine = EmbeddingEngine(mock_config)
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        mock_model.encode.return_value = np.array([0.0] * 384, dtype=np.float32)
        with patch.object(EmbeddingEngine, "model", new_callable=PropertyMock, return_value=mock_model):
            result = engine.encode_query("test query")
            assert isinstance(result, np.ndarray)
            assert result.shape == (1, 384)
