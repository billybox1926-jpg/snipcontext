"""Embedding engine and semantic-search dependency detection for SnipContext.

Handles lazy loading of the sentence-transformers model and encoding of
documents/queries into embedding vectors. Also detects at import time
whether the optional semantic-search dependencies (faiss-cpu,
sentence-transformers) are installed, so callers elsewhere in the codebase
can gracefully fall back to keyword-only search when they are not.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np

from snipcontext.config.settings import Config, get_config

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Detect optional semantic search dependencies at import time.
# When these are missing, HybridSearch gracefully falls back to keyword-only.
# ---------------------------------------------------------------------------
try:
    import faiss  # noqa: F401

    _FAISS_AVAILABLE = True
except ImportError:
    _FAISS_AVAILABLE = False

try:
    import sentence_transformers  # noqa: F401

    _SENTENCE_TRANSFORMERS_AVAILABLE = True
except (ImportError, OSError):
    # OSError catches torch DLL load failures on Windows without MSVC redist
    _SENTENCE_TRANSFORMERS_AVAILABLE = False

SEMANTIC_AVAILABLE = _FAISS_AVAILABLE and _SENTENCE_TRANSFORMERS_AVAILABLE

# ---------------------------------------------------------------------------
# Embedding engine
# ---------------------------------------------------------------------------


class EmbeddingEngine:
    """Manages the sentence-transformers model for computing embeddings.

    Lazily loads the model on first use to avoid heavy import time.
    Supports caching embeddings to disk for fast reloading.
    """

    def __init__(self, config: Config | None = None) -> None:
        self._config = config or get_config()
        self._model: SentenceTransformer | None = None
        self._model_name: str = self._config.embedding.model_name

    @property
    def model(self) -> SentenceTransformer:
        """Lazy-load the sentence-transformers model."""
        if self._model is None:
            if not SEMANTIC_AVAILABLE:
                raise ImportError(
                    "Semantic search requires the 'sentence-transformers' package. "
                    "Install it with: pip install snipcontext[semantic]"
                )
            logger.info("Loading embedding model: %s", self._model_name)
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(
                self._model_name,
                device=self._config.embedding.device,
            )
            logger.info("Embedding model loaded (%s)", self._config.embedding.device)
        return self._model

    @property
    def dimension(self) -> int:
        """Return the embedding vector dimensionality."""
        return self.model.get_sentence_embedding_dimension()

    def encode(self, texts: list[str]) -> np.ndarray:
        """Encode a list of texts into embedding vectors.

        Args:
            texts: List of strings to encode.

        Returns:
            NumPy array of shape (len(texts), dimension).
        """
        if not texts:
            return np.zeros((0, self.dimension), dtype=np.float32)

        prefixed = [f"{self._config.embedding.doc_instruction}{t}" for t in texts]
        embeddings = self.model.encode(
            prefixed,
            batch_size=self._config.embedding.batch_size,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=self._config.embedding.normalize,
        )
        return embeddings.astype(np.float32)

    def encode_query(self, query: str) -> np.ndarray:
        """Encode a single query string.

        Prepends the model-specific query instruction.
        """
        text = f"{self._config.embedding.query_instruction}{query}"
        embedding = self.model.encode(
            text,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=self._config.embedding.normalize,
        )
        return embedding.astype(np.float32).reshape(1, -1)
