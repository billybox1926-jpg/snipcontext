"""Semantic and hybrid search for SnipContext.

Implements three search strategies:
1. Semantic Search — dense vector similarity using sentence-transformers + FAISS
2. Keyword Search — TF-IDF based text matching with scikit-learn
3. Hybrid Search — weighted combination of semantic + keyword scores

All processing happens locally — no data leaves the machine.
"""

from __future__ import annotations

import logging
import pickle
import json
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

from snipcontext.core.models import SearchMode, SearchResult, Snippet
from snipcontext.config.settings import Config, get_config

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

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

        prefixed = [
            f"{self._config.embedding.doc_instruction}{t}" for t in texts
        ]
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


# ---------------------------------------------------------------------------
# FAISS vector index
# ---------------------------------------------------------------------------


class VectorIndex:
    """FAISS-based vector index for fast similarity search.

    Manages the mapping between FAISS internal IDs and SnipContext snippet IDs.
    Supports incremental add via FAISS add(). Deletion is handled by tracking
    removed IDs and filtering at search time; a full rebuild is done when
    the removal ratio exceeds a threshold.
    """

    # Fraction of deleted vectors that triggers an automatic rebuild
    REBUILD_REMOVAL_FRACTION = 0.25

    def __init__(self, config: Config | None = None) -> None:
        self._config = config or get_config()
        self._index: "faiss.Index" | None = None
        self._id_map: list[str] = []  # faiss_idx -> snippet_id
        self._removed_ids: set[str] = set()  # soft-deleted snippet IDs
        self._dimension: int | None = None

    @property
    def is_trained(self) -> bool:
        return self._index is not None and self._index.ntotal > 0

    @property
    def count(self) -> int:
        if self._index is None:
            return 0
        return self._index.ntotal - len(self._removed_ids)

    @property
    def total_raw(self) -> int:
        """Raw vector count including soft-deleted entries."""
        return self._index.ntotal if self._index else 0

    @property
    def dimension(self) -> int | None:
        return self._dimension

    @property
    def needs_rebuild(self) -> bool:
        """Return True if too many deletions have accumulated."""
        if self._index is None or self._index.ntotal == 0:
            return False
        return len(self._removed_ids) / self._index.ntotal > self.REBUILD_REMOVAL_FRACTION

    def _build_index(self, dimension: int, embeddings: "np.ndarray") -> "faiss.Index":
        """Create a new FAISS index (FlatIP or IVF depending on size)."""
        import faiss

        n = embeddings.shape[0]
        if n > 5000:
            nlist = min(int(np.sqrt(n)), 256)
            quantizer = faiss.IndexFlatIP(dimension)
            idx = faiss.IndexIVFFlat(quantizer, dimension, nlist)
            idx.train(embeddings)
        else:
            idx = faiss.IndexFlatIP(dimension)
        return idx

    def build(self, snippets: list[Snippet], embedding_engine: EmbeddingEngine) -> None:
        """Build the FAISS index from a list of snippets.

        This encodes all snippets, creates a FAISS index, and populates
        the ID mapping.
        """
        import faiss

        if not snippets:
            self._index = None
            self._id_map = []
            self._removed_ids = set()
            self._dimension = None
            return

        # Encode all snippets
        texts = [s.to_search_text() for s in snippets]
        embeddings = embedding_engine.encode(texts)
        dimension = embeddings.shape[1]
        self._dimension = dimension

        # Normalize for cosine similarity via inner product
        faiss.normalize_L2(embeddings)

        self._index = self._build_index(dimension, embeddings)
        self._index.add(embeddings)
        self._id_map = [s.id for s in snippets]
        self._removed_ids = set()

        # Store embeddings on snippets for hybrid search
        for i, snippet in enumerate(snippets):
            snippet.embedding = embeddings[i].tolist()

        logger.info(
            "Built FAISS index: %d vectors, %d dims", len(snippets), dimension
        )

    def add_vector(
        self, snippet_id: str, embedding_engine: EmbeddingEngine, text: str
    ) -> None:
        """Add a single snippet vector to the index incrementally.

        If the index has accumulated too many soft-deletions, triggers
        a full rebuild instead.

        Args:
            snippet_id: Unique ID for the snippet.
            embedding_engine: The embedding engine to encode the text.
            text: The search text to encode.
        """
        import faiss

        if snippet_id in self._removed_ids:
            self._removed_ids.discard(snippet_id)

        embedding = embedding_engine.encode([text])
        dimension = embedding.shape[1]

        if self._index is None or self._dimension is None:
            # First vector — build fresh
            faiss.normalize_L2(embedding)
            self._dimension = dimension
            self._index = self._build_index(dimension, embedding)
            self._id_map = []
            self._removed_ids = set()
        elif self.needs_rebuild:
            logger.info("Vector index: rebuild triggered due to deletion ratio")
            # Rebuild from scratch — collect all active vectors
            active = [
                sid for sid in self._id_map if sid not in self._removed_ids
            ]
            # We can't recover original vectors from FAISS FlatIP, so we
            # encode fresh. The caller must handle this — here we just
            # mark that a rebuild is needed and the HybridSearch layer
            # will call build() instead.
            self._removed_ids = set()
            raise _IncrementalRebuildNeeded()
        else:
            faiss.normalize_L2(embedding)

        self._index.add(embedding)
        self._id_map.append(snippet_id)
        logger.debug("Added vector for %s (index size: %d)", snippet_id, self._index.ntotal)

    def remove_vector(self, snippet_id: str) -> bool:
        """Mark a vector as removed (soft delete).

        FAISS FlatIP doesn't support true deletion. We track removed IDs
        and filter them at search time. A full rebuild happens automatically
        when the removal ratio exceeds REBUILD_REMOVAL_FRACTION.

        Args:
            snippet_id: The snippet ID to remove.

        Returns:
            True if the ID was found in the index.
        """
        if snippet_id not in self._id_map:
            return False
        self._removed_ids.add(snippet_id)
        logger.debug("Soft-deleted vector %s (removed: %d/%d)",
                      snippet_id, len(self._removed_ids), len(self._id_map))
        return True

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
        if not self.is_trained:
            return []

        import faiss

        # Normalize query for cosine similarity
        faiss.normalize_L2(query_embedding)

        # Search with extra room to account for soft-deleted entries
        search_k = top_k + len(self._removed_ids)
        scores, indices = self._index.search(query_embedding, min(search_k, self._index.ntotal))

        results: list[tuple[str, float]] = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(self._id_map):
                continue
            snippet_id = self._id_map[idx]
            if snippet_id in self._removed_ids:
                continue
            if score < min_score:
                continue
            results.append((snippet_id, float(score)))

        return results

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, path: Path) -> None:
        """Save the FAISS index and ID mapping to disk."""
        if self._index is None:
            return
        path.mkdir(parents=True, exist_ok=True)
        import faiss
        import json

        faiss.write_index(self._index, str(path / "vector.faiss"))
        with open(path / "idmap.json", "w") as f:
            json.dump(self._id_map, f)
        with open(path / "removed_ids.json", "w") as f:
            json.dump(list(self._removed_ids), f)
        if self._dimension is not None:
            with open(path / "dimension.json", "w") as f:
                json.dump(self._dimension, f)
        logger.debug("Saved vector index to %s", path)

    def load(self, path: Path) -> bool:
        """Load the FAISS index and ID mapping from disk.

        Returns:
            True if loaded successfully, False otherwise.
        """
        import faiss
        import json

        index_file = path / "vector.faiss"
        idmap_file = path / "idmap.json"

        if not index_file.exists() or not idmap_file.exists():
            return False

        try:
            self._index = faiss.read_index(str(index_file))
            with open(idmap_file, "r") as f:
                self._id_map = json.load(f)
            removed_file = path / "removed_ids.json"
            if removed_file.exists():
                with open(removed_file, "r") as f:
                    self._removed_ids = set(json.load(f))
            else:
                self._removed_ids = set()
            dim_file = path / "dimension.json"
            if dim_file.exists():
                with open(dim_file, "r") as f:
                    self._dimension = json.load(f)
            else:
                self._dimension = self._index.d
            logger.debug("Loaded vector index from %s", path)
            return True
        except Exception as exc:
            logger.warning("Failed to load vector index: %s", exc)
            return False


class _IncrementalRebuildNeeded(Exception):
    """Internal signal that incremental add should fall back to full rebuild."""
    pass


# ---------------------------------------------------------------------------
# Keyword index (TF-IDF)
# ---------------------------------------------------------------------------


class KeywordIndex:
    """TF-IDF based keyword search index.

    Provides fast exact and fuzzy text matching for snippet content,
    titles, descriptions, and tags.

    Incremental operations are tracked via dirty flags; the index is
    rebuilt from the pending snippet list on next modification, which is
    fast for typical snippet collections (hundreds to low thousands).
    """

    def __init__(self, config: Config | None = None) -> None:
        self._config = config or get_config()
        self._vectorizer: "sklearnTfidfVectorizer" | None = None
        self._matrix: "sparse_matrix" | None = None
        self._id_map: list[str] = []
        self._pending_adds: list[tuple[str, str]] = []  # (snippet_id, text)
        self._pending_removes: set[str] = set()
        self._dirty: bool = False

    @property
    def is_trained(self) -> bool:
        return self._vectorizer is not None and self._matrix is not None

    @property
    def is_dirty(self) -> bool:
        """Return True if there are pending incremental changes."""
        return self._dirty or bool(self._pending_adds or self._pending_removes)

    @property
    def count(self) -> int:
        base = self._matrix.shape[0] if self._matrix is not None else 0
        return base + len(self._pending_adds) - len(self._pending_removes)

    def build(self, snippets: list[Snippet]) -> None:
        """Build the TF-IDF index from snippets."""
        from sklearn.feature_extraction.text import TfidfVectorizer

        if not snippets:
            self._vectorizer = None
            self._matrix = None
            self._id_map = []
            self._pending_adds = []
            self._pending_removes = set()
            self._dirty = False
            return

        texts = [s.to_search_text() for s in snippets]
        self._vectorizer = TfidfVectorizer(
            lowercase=True,
            stop_words="english",
            ngram_range=(1, 2),  # Unigrams + bigrams
            max_features=10000,
            min_df=1,
            dtype=np.float32,
        )
        self._matrix = self._vectorizer.fit_transform(texts)
        self._id_map = [s.id for s in snippets]
        self._pending_adds = []
        self._pending_removes = set()
        self._dirty = False

        logger.info(
            "Built keyword index: %d docs, %d terms",
            len(snippets),
            len(self._vectorizer.vocabulary_),
        )

    def _apply_pending(self) -> None:
        """Rebuild the index to apply pending adds/removes."""
        if not self.is_dirty:
            return

        # Build full list: existing (minus removes) + adds
        active_ids = [sid for sid in self._id_map if sid not in self._pending_removes]
        all_ids = active_ids + [sid for sid, _ in self._pending_adds]

        if not all_ids:
            self._vectorizer = None
            self._matrix = None
            self._id_map = []
            self._pending_adds = []
            self._pending_removes = set()
            self._dirty = False
            return

        # We need the actual texts. For existing items we don't have them
        # cached, so we need the caller to provide them. The HybridSearch
        # layer handles this by calling build() with full snippet list.
        # Here we just mark dirty and let the orchestrator rebuild.
        logger.debug("Keyword index: %d pending adds, %d pending removes",
                      len(self._pending_adds), len(self._pending_removes))

    def add_doc(self, snippet_id: str, text: str) -> None:
        """Queue a document for incremental addition.

        The document is added to the pending list and will be included
        in the index on the next rebuild (triggered automatically by
        search or explicit rebuild).
        """
        # If this ID was pending removal, cancel the removal
        self._pending_removes.discard(snippet_id)
        # Remove any existing pending add for this ID
        self._pending_adds = [(sid, t) for sid, t in self._pending_adds if sid != snippet_id]
        self._pending_adds.append((snippet_id, text))
        self._dirty = True
        logger.debug("Keyword index: queued add for %s", snippet_id)

    def remove_doc(self, snippet_id: str) -> bool:
        """Queue a document for incremental removal."""
        if snippet_id not in self._id_map:
            return False
        self._pending_removes.add(snippet_id)
        # Remove any pending add for this ID
        self._pending_adds = [(sid, t) for sid, t in self._pending_adds if sid != snippet_id]
        self._dirty = True
        logger.debug("Keyword index: queued remove for %s", snippet_id)
        return True

    def search(
        self,
        query: str,
        top_k: int,
        min_score: float = 0.0,
    ) -> list[tuple[str, float]]:
        """Search by keyword relevance.

        Returns:
            List of (snippet_id, score) tuples.
        """
        if not self.is_trained:
            return []

        from sklearn.metrics.pairwise import cosine_similarity

        query_vec = self._vectorizer.transform([query])
        similarities = cosine_similarity(query_vec, self._matrix)[0]

        # Get top-k indices
        if top_k >= len(similarities):
            top_indices = np.argsort(similarities)[::-1]
        else:
            top_indices = np.argpartition(similarities, -top_k)[-top_k:]
            top_indices = top_indices[np.argsort(similarities[top_indices])[::-1]]

        results: list[tuple[str, float]] = []
        for idx in top_indices:
            snippet_id = self._id_map[idx]
            if snippet_id in self._pending_removes:
                continue
            score = float(similarities[idx])
            if score < min_score:
                continue
            results.append((snippet_id, score))

        # Also search pending adds (brute-force, typically very few)
        if self._pending_adds:
            from sklearn.feature_extraction.text import TfidfVectorizer as _Tfidf
            # For small pending lists, compute similarity directly
            pending_texts = [text for _, text in self._pending_adds]
            # Use the existing vectorizer's vocabulary for consistency
            try:
                pending_vecs = self._vectorizer.transform(pending_texts)
                pending_sims = cosine_similarity(query_vec, pending_vecs)[0]
                for i, (sid, _) in enumerate(self._pending_adds):
                    score = float(pending_sims[i])
                    if score >= min_score:
                        results.append((sid, score))
            except Exception:
                pass  # Vocabulary mismatch — skip pending adds

        # Re-sort and trim
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def save(self, path: Path) -> None:
        """Save the keyword index to disk."""
        if not self.is_trained:
            return
        path.mkdir(parents=True, exist_ok=True)
        with open(path / "keyword_index.pkl", "wb") as f:
            pickle.dump(
                {
                    "vectorizer": self._vectorizer,
                    "matrix": self._matrix,
                    "id_map": self._id_map,
                },
                f,
            )
        logger.debug("Saved keyword index to %s", path)

    def load(self, path: Path) -> bool:
        """Load the keyword index from disk."""
        index_file = path / "keyword_index.pkl"
        if not index_file.exists():
            return False
        try:
            with open(index_file, "rb") as f:
                data = pickle.load(f)
            self._vectorizer = data["vectorizer"]
            self._matrix = data["matrix"]
            self._id_map = data["id_map"]
            self._pending_adds = []
            self._pending_removes = set()
            self._dirty = False
            logger.debug("Loaded keyword index from %s", path)
            return True
        except Exception as exc:
            logger.warning("Failed to load keyword index: %s", exc)
            return False


# ---------------------------------------------------------------------------
# Unified search orchestrator
# ---------------------------------------------------------------------------


class SemanticSearch:
    """Pure semantic (dense vector) search."""

    def __init__(self, config: Config | None = None) -> None:
        self._config = config or get_config()
        self.embedder = EmbeddingEngine(config)
        self.vector_index = VectorIndex(config)

    def index_snippets(self, snippets: list[Snippet]) -> None:
        """Build the semantic search index from snippets."""
        self.vector_index.build(snippets, self.embedder)
        self.vector_index.save(self._config.index_path)

    def search(self, query: str, top_k: int | None = None) -> list[SearchResult]:
        """Search by semantic similarity."""
        from snipcontext.core.storage import StorageEngine

        top_k = top_k or self._config.search.top_k
        storage = StorageEngine(self._config)

        query_embedding = self.embedder.encode_query(query)
        results = self.vector_index.search(
            query_embedding,
            top_k=top_k,
            min_score=self._config.search.min_score,
        )

        search_results: list[SearchResult] = []
        for snippet_id, score in results:
            try:
                snippet = storage.get(snippet_id)
                snippet.record_access()
                storage.save(snippet)
                search_results.append(
                    SearchResult(
                        snippet=snippet,
                        score=score,
                        matched_by="semantic",
                    )
                )
            except Exception:
                continue

        return search_results


class HybridSearch:
    """Combines semantic and keyword search with configurable weighting.

    Uses a weighted score fusion:
        final_score = w_sem * semantic_score + w_kw * keyword_score

    This gives the best of both worlds — semantic understanding of intent
    plus precise keyword matching for specific terms.

    Supports incremental indexing: add_snippet(), remove_snippet(), and
    update_snippet() modify the indices without a full rebuild. The keyword
    index auto-rebuilds when dirty; the vector index uses soft-delete with
    automatic rebuild when the deletion ratio exceeds a threshold.
    """

    def __init__(self, config: Config | None = None) -> None:
        self._config = config or get_config()
        self.embedder = EmbeddingEngine(config)
        self.vector_index = VectorIndex(config)
        self.keyword_index = KeywordIndex(config)
        self._dirty: bool = False

    @property
    def is_dirty(self) -> bool:
        """Return True if indices have pending incremental changes."""
        return self._dirty or self.keyword_index.is_dirty

    def index_snippets(self, snippets: list[Snippet]) -> None:
        """Build both semantic and keyword indices."""
        try:
            self.vector_index.build(snippets, self.embedder)
            self.vector_index.save(self._config.index_path)
        except ImportError:
            logger.warning("FAISS not available, semantic index disabled")

        self.keyword_index.build(snippets)
        self.keyword_index.save(self._config.index_path)
        self._dirty = False

    def add_snippet(self, snippet: Snippet) -> None:
        """Incrementally add a snippet to both indices.

        For the vector index, encodes and adds the snippet embedding.
        For the keyword index, queues the document for inclusion.
        """
        text = snippet.to_search_text()

        # Vector index: try incremental add, fall back to rebuild
        try:
            self.vector_index.add_vector(snippet.id, self.embedder, text)
        except _IncrementalRebuildNeeded:
            logger.info("Incremental add: falling back to full vector rebuild")
            all_snippets = self._load_all_for_rebuild(snippet)
            self.vector_index.build(all_snippets, self.embedder)
            self.vector_index.save(self._config.index_path)
        except ImportError:
            pass  # FAISS not available

        # Keyword index: queue incremental add
        self.keyword_index.add_doc(snippet.id, text)

        # If keyword index is dirty with enough items, rebuild
        if self.keyword_index.is_dirty:
            all_snippets = None
            # Check if we have pending adds that need hydration
            if self.keyword_index._pending_adds:
                try:
                    all_snippets = self._load_all_for_rebuild()
                except Exception:
                    pass
            if all_snippets is not None:
                self.keyword_index.build(all_snippets)
                self.keyword_index.save(self._config.index_path)
            self._dirty = False

        logger.debug("Incrementally added snippet %s", snippet.id)

    def remove_snippet(self, snippet_id: str) -> bool:
        """Incrementally remove a snippet from both indices."""
        v_ok = self.vector_index.remove_vector(snippet_id)
        k_ok = self.keyword_index.remove_doc(snippet_id)

        # If vector index needs rebuild (too many deletions), do it
        if self.vector_index.needs_rebuild:
            try:
                all_snippets = self._load_all_for_rebuild()
                self.vector_index.build(all_snippets, self.embedder)
                self.vector_index.save(self._config.index_path)
            except Exception:
                pass

        # Rebuild keyword index if dirty
        if self.keyword_index.is_dirty:
            try:
                all_snippets = self._load_all_for_rebuild()
                if all_snippets:
                    self.keyword_index.build(all_snippets)
                    self.keyword_index.save(self._config.index_path)
                else:
                    self.keyword_index.build([])
            except Exception:
                pass

        self._dirty = False
        logger.debug("Removed snippet %s (v=%s, k=%s)", snippet_id, v_ok, k_ok)
        return v_ok or k_ok

    def update_snippet(self, snippet: Snippet) -> None:
        """Update a snippet's index entries (remove old, add new)."""
        self.remove_snippet(snippet.id)
        self.add_snippet(snippet)

    def _load_all_for_rebuild(self, extra: Snippet | None = None) -> list[Snippet]:
        """Load all snippets from storage for index rebuild."""
        from snipcontext.core.storage import StorageEngine
        storage = StorageEngine(self._config)
        snippets = storage.list_all()
        if extra is not None and extra.id not in {s.id for s in snippets}:
            snippets.append(extra)
        return snippets

    def _ensure_vectors_current(self) -> None:
        """If vector index needs rebuild due to deletions, rebuild now."""
        if self.vector_index.needs_rebuild and self.vector_index.is_trained:
            try:
                all_snippets = self._load_all_for_rebuild()
                self.vector_index.build(all_snippets, self.embedder)
                self.vector_index.save(self._config.index_path)
            except Exception:
                pass

    def search(
        self,
        query: str,
        top_k: int | None = None,
        mode: SearchMode | str | None = None,
    ) -> list[SearchResult]:
        """Execute search using the specified or default strategy.

        Args:
            query: The search query string.
            top_k: Maximum number of results. Defaults to config.
            mode: Override search strategy. Defaults to config default_mode.

        Returns:
            Ranked list of SearchResult objects.
        """
        from snipcontext.core.storage import StorageEngine

        top_k = top_k or self._config.search.top_k
        mode = SearchMode(mode or self._config.search.default_mode)
        storage = StorageEngine(self._config)

        if mode == SearchMode.TAG:
            return self._tag_search(query, top_k, storage)

        if mode == SearchMode.KEYWORD:
            return self._keyword_search(query, top_k, storage)

        if mode == SearchMode.SEMANTIC:
            return self._semantic_search(query, top_k, storage)

        # HYBRID mode
        return self._hybrid_search(query, top_k, storage)

    def _semantic_search(
        self, query: str, top_k: int, storage: "StorageEngine"
    ) -> list[SearchResult]:
        """Pure semantic search path."""
        query_embedding = self.embedder.encode_query(query)
        raw = self.vector_index.search(query_embedding, top_k=top_k * 2)
        return self._hydrate(raw, "semantic", top_k, storage)

    def _keyword_search(
        self, query: str, top_k: int, storage: "StorageEngine"
    ) -> list[SearchResult]:
        """Pure keyword search path."""
        raw = self.keyword_index.search(query, top_k=top_k * 2)
        return self._hydrate(raw, "keyword", top_k, storage)

    def _hybrid_search(
        self, query: str, top_k: int, storage: "StorageEngine"
    ) -> list[SearchResult]:
        """Weighted fusion of semantic and keyword scores."""
        w_sem = self._config.search.semantic_weight
        w_kw = self._config.search.keyword_weight

        # Ensure vector index is current before hybrid search
        self._ensure_vectors_current()

        # Semantic results (if index available)
        sem_scores: dict[str, float] = {}
        if self.vector_index.is_trained:
            try:
                query_embedding = self.embedder.encode_query(query)
                sem_raw = self.vector_index.search(query_embedding, top_k=top_k * 3)
                sem_scores = {sid: s for sid, s in sem_raw}
            except Exception:
                pass  # Fall back to keyword-only

        # Keyword results
        kw_raw = self.keyword_index.search(query, top_k=top_k * 3)
        kw_scores: dict[str, float] = {sid: s for sid, s in kw_raw}

        # If no semantic results available, do keyword-only
        if not sem_scores:
            return self._hydrate(
                sorted(kw_scores.items(), key=lambda x: x[1], reverse=True)[:top_k],
                "keyword", top_k, storage
            )

        # Fuse scores
        all_ids = set(sem_scores.keys()) | set(kw_scores.keys())
        fused: list[tuple[str, float]] = []
        for sid in all_ids:
            score = w_sem * sem_scores.get(sid, 0.0) + w_kw * kw_scores.get(sid, 0.0)
            if score >= self._config.search.min_score:
                fused.append((sid, score))

        fused.sort(key=lambda x: x[1], reverse=True)
        return self._hydrate(fused[:top_k], "hybrid", top_k, storage)

    def _tag_search(
        self, query: str, top_k: int, storage: "StorageEngine"
    ) -> list[SearchResult]:
        """Exact tag match search."""
        tag = query.strip().lstrip("#").lower()
        snippets = storage.find_by_tag(tag)
        results: list[SearchResult] = []
        for snippet in snippets[:top_k]:
            snippet.record_access()
            storage.save(snippet)
            results.append(
                SearchResult(
                    snippet=snippet,
                    score=1.0,
                    matched_by="tag",
                    highlights=[f"#{tag}"],
                )
            )
        return results

    def _hydrate(
        self,
        raw_results: list[tuple[str, float]],
        matched_by: str,
        top_k: int,
        storage: "StorageEngine",
    ) -> list[SearchResult]:
        """Convert raw ID+score pairs into SearchResult objects."""
        search_results: list[SearchResult] = []
        seen = set()

        for snippet_id, score in raw_results:
            if snippet_id in seen:
                continue
            seen.add(snippet_id)

            try:
                snippet = storage.get(snippet_id)
            except Exception:
                continue

            snippet.record_access()
            storage.save(snippet)

            search_results.append(
                SearchResult(
                    snippet=snippet,
                    score=min(score, 1.0),
                    matched_by=matched_by,  # type: ignore[arg-type]
                )
            )

            if len(search_results) >= top_k:
                break

        return search_results

    def is_indexed(self) -> bool:
        """Check if both indices are built and ready."""
        return self.vector_index.is_trained and self.keyword_index.is_trained

    def load_indices(self) -> bool:
        """Attempt to load persisted indices from disk."""
        try:
            v_ok = self.vector_index.load(self._config.index_path)
        except ImportError:
            v_ok = False
        try:
            k_ok = self.keyword_index.load(self._config.index_path)
        except ImportError:
            k_ok = False
        return v_ok and k_ok
