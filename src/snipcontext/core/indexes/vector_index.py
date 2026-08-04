"""FAISS-backed vector search index for SnipContext."""

from __future__ import annotations

import hashlib
import json
import logging
from typing import TYPE_CHECKING

import numpy as np

from snipcontext.config.settings import Config, get_config
from snipcontext.core.embeddings import SEMANTIC_AVAILABLE, EmbeddingEngine
from snipcontext.core.index_backends import IndexBackend
from snipcontext.core.models import Snippet

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# FAISS vector index
# ---------------------------------------------------------------------------


class VectorIndex:
    """Vector search index backed by a pluggable ``IndexBackend`` implementation.

    The public API is unchanged from the previous FAISS-specific version so
    that existing tests and callers continue to work without modification.
    """

    def __init__(self, config: Config | None = None) -> None:
        self._config = config or get_config()
        self._backend: IndexBackend | None = None
        self._content_hashes: dict[str, str] = {}
        self._id_set: set[str] = set()

    @property
    def is_trained(self) -> bool:
        return self._backend is not None and self._backend.is_trained

    @property
    def count(self) -> int:
        return self._backend.count if self._backend else 0

    @property
    def snippet_ids(self) -> tuple[str, ...]:
        return tuple(self._backend.snippet_ids if self._backend else [])

    def build(self, snippets: list[Snippet], embedding_engine: EmbeddingEngine) -> None:
        """Build the vector index from a list of snippets.

        The backend is selected from ``SearchConfig.index_type`` and trained
        before the provided vectors are added.
        """
        if not SEMANTIC_AVAILABLE:
            raise ImportError(
                "Vector index (FAISS) is unavailable. "
                "Install semantic search dependencies with: pip install snipcontext[semantic]"
            )

        from snipcontext.core.index_backends import _create_backend

        if not snippets:
            self._backend = None
            self._content_hashes = {}
            self._id_set = set()
            return

        texts = [s.to_search_text() for s in snippets]
        embeddings = embedding_engine.encode(texts)
        dimension = embeddings.shape[1]
        try:
            import faiss
        except ImportError as exc:
            raise ImportError(
                "Semantic search requires the 'faiss-cpu' package. "
                "Install it with: pip install snipcontext[semantic]"
            ) from exc
        faiss.normalize_L2(embeddings)

        backend = _create_backend(
            self._config,
            dimension,
            snippet_count=len(snippets),
            auto_switch=self._config.search.auto_switch,
        )
        backend.train(embeddings)
        backend.add(embeddings, [s.id for s in snippets])

        self._backend = backend
        self._content_hashes = {
            s.id: hashlib.sha256(s.content.encode()).hexdigest()[:16] for s in snippets
        }
        self._id_set = {s.id for s in snippets}

        # Store embeddings on snippets for hybrid search
        for i, snippet in enumerate(snippets):
            snippet.embedding = embeddings[i].tolist()

        logger.info("Built vector index: %d vectors, %d dims", len(snippets), dimension)

    def add_vector(self, snippet: Snippet, embedding_engine: EmbeddingEngine | None = None) -> None:
        """Incrementally add a single snippet embedding to the vector index."""
        if not SEMANTIC_AVAILABLE:
            raise ImportError(
                "Vector index (FAISS) is unavailable. "
                "Install semantic search dependencies with: pip install snipcontext[semantic]"
            )

        if self._backend is None:
            raise RuntimeError("Vector index is not initialized")

        if snippet.id in self._id_set:
            self.remove_vector(snippet.id)

        if embedding_engine is not None:
            text = f"{self._config.embedding.doc_instruction}{snippet.content}"
            embedding = (
                embedding_engine.model.encode(
                    text,
                    show_progress_bar=False,
                    convert_to_numpy=True,
                    normalize_embeddings=self._config.embedding.normalize,
                )
                .astype(np.float32)
                .flatten()
            )
        else:
            embedding = self._embed_fn(snippet.content)

        vec = np.array([embedding], dtype=np.float32)
        import faiss

        faiss.normalize_L2(vec)
        self._backend.add(vec, [snippet.id])
        self._id_set.add(snippet.id)
        self._content_hashes[snippet.id] = hashlib.sha256(snippet.content.encode()).hexdigest()[:16]

    def remove_vector(self, snippet_id: str) -> None:
        """Remove a single snippet from the vector index."""
        if not SEMANTIC_AVAILABLE:
            return

        if self._backend is None or snippet_id not in self._id_set:
            return

        self._backend.remove([snippet_id])
        self._id_set.discard(snippet_id)
        self._content_hashes.pop(snippet_id, None)

    def search(
        self,
        query_embedding: np.ndarray,
        top_k: int,
        min_score: float = 0.0,
    ) -> list[tuple[str, float]]:
        """Search the index for similar vectors.

        Returns:
            List of (snippet_id, score) tuples, sorted by score descending.
        """
        if not self.is_trained or not SEMANTIC_AVAILABLE:
            return []

        import faiss

        query = np.ascontiguousarray(query_embedding, dtype=np.float32)
        faiss.normalize_L2(query)

        raw = self._backend.search(query, top_k) if self._backend else []
        results: list[tuple[str, float]] = []
        for snippet_id, score in raw:
            if score < min_score:
                continue
            results.append((snippet_id, float(score)))
        return results

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, path: Path) -> None:
        """Save the vector index and content hashes to disk."""
        if self._backend is None or not SEMANTIC_AVAILABLE:
            return
        self._backend.save(path)
        hash_path = path / "content_hashes.json"
        hash_path.write_text(json.dumps(self._content_hashes), encoding="utf-8")
        logger.debug("Saved vector index to %s", path)

    def load(self, path: Path) -> bool:
        """Load the vector index and content hashes from disk.

        Returns:
            True if loaded successfully, False otherwise.
        """
        if not SEMANTIC_AVAILABLE:
            return False

        if self._backend is None:
            return False

        loaded = self._backend.load(path)
        if not loaded:
            return False

        self._id_set = set(self._backend.snippet_ids)
        hash_path = path / "content_hashes.json"
        if hash_path.exists():
            self._content_hashes = json.loads(hash_path.read_text(encoding="utf-8"))
        else:
            self._content_hashes = {}

        logger.debug("Loaded vector index from %s", path)
        return True

    def _embed_fn(self, text: str) -> np.ndarray:
        if not SEMANTIC_AVAILABLE:
            raise ImportError(
                "Semantic embedding requires 'sentence-transformers'. "
                "Install it with: pip install snipcontext[semantic]"
            )
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer(
            self._config.embedding.model_name,
            device=self._config.embedding.device,
        )
        text = f"{self._config.embedding.doc_instruction}{text}"
        embedding = model.encode(
            text,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=self._config.embedding.normalize,
        )
        return embedding.astype(np.float32).reshape(1, -1).flatten()
