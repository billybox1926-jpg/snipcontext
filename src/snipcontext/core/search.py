"""Semantic and hybrid search for SnipContext.

Implements three search strategies:
1. Semantic Search — dense vector similarity using sentence-transformers + FAISS
2. Keyword Search — TF-IDF based text matching with scikit-learn
3. Hybrid Search — weighted combination of semantic + keyword scores

All processing happens locally — no data leaves the machine.
"""

from __future__ import annotations

import json
import logging
import pickle
from typing import TYPE_CHECKING

import numpy as np

from snipcontext.config.settings import Config, get_config
from snipcontext.core.models import SearchMode, SearchResult, Snippet
from snipcontext.core.storage import StorageError

if TYPE_CHECKING:
    from pathlib import Path

    import faiss
    from scipy.sparse import spmatrix
    from sentence_transformers import SentenceTransformer
    from sklearn.feature_extraction.text import TfidfVectorizer

    from snipcontext.core.storage import StorageEngine

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


# ---------------------------------------------------------------------------
# FAISS vector index
# ---------------------------------------------------------------------------


class VectorIndex:
    """FAISS-based vector index for fast similarity search.

    Manages the mapping between FAISS internal IDs and SnipContext snippet IDs.
    """

    def __init__(self, config: Config | None = None) -> None:
        self._config = config or get_config()
        self._index: faiss.Index | None = None
        self._id_map: list[str] = []  # faiss_idx -> snippet_id

    @property
    def is_trained(self) -> bool:
        return self._index is not None and self._index.ntotal > 0

    @property
    def count(self) -> int:
        return self._index.ntotal if self._index else 0

    def build(self, snippets: list[Snippet], embedding_engine: EmbeddingEngine) -> None:
        """Build the FAISS index from a list of snippets.

        This encodes all snippets, creates a FAISS index, and populates
        the ID mapping.
        """
        import faiss

        if not snippets:
            self._index = None
            self._id_map = []
            return

        # Encode all snippets
        texts = [s.to_search_text() for s in snippets]
        embeddings = embedding_engine.encode(texts)
        dimension = embeddings.shape[1]

        # Normalize for cosine similarity via inner product
        faiss.normalize_L2(embeddings)

        # Use IndexFlatIP for exact search (cosine similarity)
        if len(snippets) > 5000:
            # IVF for larger collections
            nlist = min(int(np.sqrt(len(snippets))), 256)
            quantizer = faiss.IndexFlatIP(dimension)
            index = faiss.IndexIVFFlat(quantizer, dimension, nlist)
            index.train(embeddings)
        else:
            index = faiss.IndexFlatIP(dimension)

        index.add(embeddings)
        self._id_map = [s.id for s in snippets]
        self._index = index

        # Store embeddings on snippets for hybrid search
        for i, snippet in enumerate(snippets):
            snippet.embedding = embeddings[i].tolist()

        logger.info("Built FAISS index: %d vectors, %d dims", len(snippets), dimension)

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

        assert self._index is not None
        # Normalize query for cosine similarity
        faiss.normalize_L2(query_embedding)

        scores, indices = self._index.search(query_embedding, top_k)

        results: list[tuple[str, float]] = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(self._id_map):
                continue
            if score < min_score:
                continue
            results.append((self._id_map[idx], float(score)))

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

        faiss.write_index(self._index, str(path / "vector.faiss"))
        with open(path / "idmap.json", "w") as f:
            json_str = '"' + '", "'.join(self._id_map) + '"'
            f.write(f"[{json_str}]")
        logger.debug("Saved vector index to %s", path)

    def load(self, path: Path) -> bool:
        """Load the FAISS index and ID mapping from disk.

        Returns:
            True if loaded successfully, False otherwise.
        """

        index_file = path / "vector.faiss"
        idmap_file = path / "idmap.json"

        if not index_file.exists() or not idmap_file.exists():
            logger.debug("Index files not found at %s", path)
            return False

        try:
            import faiss

            self._index = faiss.read_index(str(index_file))
            with open(idmap_file) as f:
                self._id_map = json.load(f)

            # Validate index integrity
            if self._index.ntotal != len(self._id_map):
                logger.warning(
                    "Index ID map length mismatch: %d vectors vs %d IDs",
                    self._index.ntotal,
                    len(self._id_map),
                )
                return False

            logger.debug("Loaded vector index from %s", path)
            return True
        except Exception as exc:
            logger.warning("Failed to load vector index from %s: %s", path, exc)
            # Clean up potentially corrupted files
            try:
                if index_file.exists():
                    index_file.unlink()
                if (path / "idmap.json").exists():
                    (path / "idmap.json").unlink()
            except Exception:
                pass
            return False


# ---------------------------------------------------------------------------
# Keyword index (TF-IDF)
# ---------------------------------------------------------------------------


class KeywordIndex:
    """TF-IDF based keyword search index.

    Provides fast exact and fuzzy text matching for snippet content,
    titles, descriptions, and tags.
    """

    def __init__(self, config: Config | None = None) -> None:
        self._config = config or get_config()
        self._vectorizer: TfidfVectorizer | None = None
        self._matrix: spmatrix | None = None
        self._id_map: list[str] = []
        self._texts: list[str] = []

    @property
    def is_trained(self) -> bool:
        return self._vectorizer is not None and self._matrix is not None

    def build(self, snippets: list[Snippet]) -> None:
        """Build the TF-IDF index from snippets."""
        from sklearn.feature_extraction.text import TfidfVectorizer

        if not snippets:
            self._vectorizer = None
            self._matrix = None
            self._id_map = []
            return

        texts = [s.to_search_text() for s in snippets]
        self._texts = texts  # Store for fuzzy matching
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

        logger.info(
            "Built keyword index: %d docs, %d terms",
            len(snippets),
            len(self._vectorizer.vocabulary_),
        )

    def search(
        self,
        query: str,
        top_k: int,
        min_score: float = 0.0,
        fuzzy: bool = False,
    ) -> list[tuple[str, float]]:
        """Search by keyword relevance.

        Args:
            query: The search query string.
            top_k: Maximum number of results.
            min_score: Minimum similarity score (0.0 to 1.0).
            fuzzy: Enable fuzzy matching with rapidfuzz.

        Returns:
            List of (snippet_id, score) tuples sorted by relevance.
        """
        if not self.is_trained:
            return []

        from sklearn.metrics.pairwise import cosine_similarity

        assert self._vectorizer is not None
        assert self._matrix is not None
        query_vec = self._vectorizer.transform([query])
        similarities = cosine_similarity(query_vec, self._matrix)[0]

        if fuzzy:
            # Augment with fuzzy matching against original texts
            try:
                fuzzy_scores = self._fuzzy_search(query, top_k, min_score)
                # Merge TF-IDF and fuzzy scores
                for idx, f_score in fuzzy_scores:
                    # Blend: 70% TF-IDF, 30% fuzzy
                    tfidf_score = float(similarities[idx]) if idx < len(similarities) else 0.0
                    blended = 0.7 * tfidf_score + 0.3 * f_score
                    similarities[idx] = blended
            except ImportError:
                pass  # rapidfuzz not available, skip fuzzy matching

        # Get top-k indices
        if top_k >= len(similarities):
            top_indices = np.argsort(similarities)[::-1]
        else:
            top_indices = np.argpartition(similarities, -top_k)[-top_k:]
            top_indices = top_indices[np.argsort(similarities[top_indices])[::-1]]

        results: list[tuple[str, float]] = []
        for idx in top_indices:
            score = float(similarities[idx])
            if score < min_score:
                continue
            results.append((self._id_map[idx], score))

        return results

    def _fuzzy_search(self, query: str, top_k: int, min_score: float) -> list[tuple[int, float]]:
        """Perform fuzzy matching against stored texts.

        Returns:
            List of (index, normalized_score) tuples.
        """
        if not self._texts:
            return []

        try:
            from rapidfuzz import fuzz, process

            # Use token_set_ratio for better matching of code snippets
            # This handles reordered words and partial matches well
            results = process.extract(
                query,
                self._texts,
                scorer=fuzz.token_set_ratio,
                limit=top_k * 2,
                score_cutoff=int(min_score * 100),
            )

            # Normalize scores to 0-1 range
            normalized = [(idx, score / 100.0) for _, score, idx in results]
            return normalized
        except ImportError:
            return []

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
                    "texts": self._texts,
                },
                f,
            )
        logger.debug("Saved keyword index to %s", path)

    def load(self, path: Path) -> bool:
        """Load the keyword index from disk."""
        index_file = path / "keyword_index.pkl"
        if not index_file.exists():
            logger.debug("Keyword index file not found at %s", path)
            return False
        try:
            with open(index_file, "rb") as f:
                data = pickle.load(f)
            self._vectorizer = data["vectorizer"]
            self._matrix = data["matrix"]
            self._id_map = data["id_map"]
            self._texts = data.get("texts", [])

            # Validate index integrity
            if self._matrix is not None and len(self._id_map) != self._matrix.shape[0]:
                logger.warning(
                    "Keyword index ID map length mismatch: %d IDs vs %d rows",
                    len(self._id_map),
                    self._matrix.shape[0],
                )
                return False

            logger.debug("Loaded keyword index from %s", path)
            return True
        except Exception as exc:
            logger.warning("Failed to load keyword index from %s: %s", path, exc)
            # Clean up potentially corrupted file
            try:
                if index_file.exists():
                    index_file.unlink()
            except Exception:
                pass
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
        results = self.vector_index.search(query_embedding, top_k=top_k, min_score=0.0)
        return self._hydrate(results, "semantic", top_k, storage)

    def _hydrate(
        self,
        raw_results: list[tuple[str, float]],
        matched_by: str,
        top_k: int,
        storage: StorageEngine,
    ) -> list[SearchResult]:
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
                    matched_by=matched_by,
                )
            )

            if len(search_results) >= top_k:
                break

        return search_results


class HybridSearch:
    """Combines semantic and keyword search with configurable weighting.

    Uses a weighted score fusion:
        final_score = w_sem * semantic_score + w_kw * keyword_score

    This gives the best of both worlds — semantic understanding of intent
    plus precise keyword matching for specific terms.
    """

    def __init__(self, config: Config | None = None) -> None:
        self._config = config or get_config()
        self.embedder = EmbeddingEngine(config)
        self.vector_index = VectorIndex(config)
        self.keyword_index = KeywordIndex(config)

    def load_indices(self) -> tuple[bool, bool]:
        """Load existing search indices from disk.

        Returns:
            Tuple of (semantic_loaded, keyword_loaded).
        """
        semantic_loaded = self.vector_index.load(self._config.index_path)
        keyword_loaded = self.keyword_index.load(self._config.index_path)

        if semantic_loaded and keyword_loaded:
            logger.debug("Loaded existing search indices from %s", self._config.index_path)

        return semantic_loaded, keyword_loaded

    def index_snippets(self, snippets: list[Snippet]) -> None:
        """Build both semantic and keyword indices.

        If semantic index fails to load or build, falls back to keyword-only.
        """
        # Try to load existing indices first
        semantic_loaded = self.vector_index.load(self._config.index_path)
        keyword_loaded = self.keyword_index.load(self._config.index_path)

        # If both loaded successfully and we're not forcing rebuild, return
        if semantic_loaded and keyword_loaded:
            logger.debug("Loaded existing search indices from %s", self._config.index_path)
            return

        logger.info("Rebuilding search indices (%d snippets)", len(snippets))

        # Try to build semantic index
        semantic_ok = False
        try:
            self.vector_index.build(snippets, self.embedder)
            self.vector_index.save(self._config.index_path)
            semantic_ok = True
        except (ImportError, OSError) as exc:
            logger.warning("Semantic index build failed: %s", exc)
            logger.info("Falling back to keyword-only search")

        # Always build keyword index as fallback
        try:
            self.keyword_index.build(snippets)
            self.keyword_index.save(self._config.index_path)
        except Exception as exc:
            logger.error("Keyword index build failed: %s", exc)
            raise StorageError(f"Failed to build keyword index: {exc}") from exc

        if not semantic_ok:
            logger.info("Built keyword-only index (semantic unavailable)")
        else:
            logger.info("Built hybrid search indices (semantic + keyword)")

    def search(
        self,
        query: str,
        top_k: int | None = None,
        mode: SearchMode | str | None = None,
        min_score: float | None = None,
        fuzzy: bool = False,
    ) -> list[SearchResult]:
        """Execute search using the specified or default strategy.

        Args:
            query: The search query string.
            top_k: Maximum number of results. Defaults to config.
            mode: Override search strategy. Defaults to config default_mode.
            min_score: Minimum relevance score threshold. Defaults to config.min_score.
            fuzzy: Enable fuzzy matching for keyword search.

        Returns:
            Ranked list of SearchResult objects.
        """
        from snipcontext.core.storage import StorageEngine

        top_k = top_k or self._config.search.top_k
        mode = SearchMode(mode or self._config.search.default_mode)
        min_score = min_score if min_score is not None else self._config.search.min_score
        storage = StorageEngine(self._config)

        if mode == SearchMode.TAG:
            return self._tag_search(query, top_k, storage)

        if mode == SearchMode.KEYWORD:
            return self._keyword_search(query, top_k, min_score, fuzzy, storage)

        if mode == SearchMode.SEMANTIC:
            return self._semantic_search(query, top_k, min_score, storage)

        # HYBRID mode
        return self._hybrid_search(query, top_k, min_score, fuzzy, storage)

    def _semantic_search(
        self, query: str, top_k: int, min_score: float, storage: StorageEngine
    ) -> list[SearchResult]:
        """Pure semantic search path."""
        query_embedding = self.embedder.encode_query(query)
        raw = self.vector_index.search(query_embedding, top_k=top_k * 2, min_score=min_score)
        return self._hydrate(raw, "semantic", top_k, storage)

    def _keyword_search(
        self, query: str, top_k: int, min_score: float, fuzzy: bool, storage: StorageEngine
    ) -> list[SearchResult]:
        """Pure keyword search path."""
        raw = self.keyword_index.search(query, top_k=top_k * 2, min_score=min_score, fuzzy=fuzzy)
        return self._hydrate(raw, "keyword", top_k, storage)

    def _hybrid_search(
        self,
        query: str,
        top_k: int,
        min_score: float,
        fuzzy: bool,
        storage: StorageEngine,
    ) -> list[SearchResult]:
        """Weighted fusion of semantic and keyword scores."""
        w_sem = self._config.search.semantic_weight
        w_kw = self._config.search.keyword_weight

        # Semantic results (if index available)
        sem_scores: dict[str, float] = {}
        if self.vector_index.is_trained:
            try:
                query_embedding = self.embedder.encode_query(query)
                sem_raw = self.vector_index.search(
                    query_embedding, top_k=top_k * 3, min_score=min_score
                )
                sem_scores = dict(sem_raw)
            except Exception:
                pass  # Fall back to keyword-only

        # Keyword results
        kw_raw = self.keyword_index.search(query, top_k=top_k * 3, min_score=min_score, fuzzy=fuzzy)
        kw_scores: dict[str, float] = dict(kw_raw)

        # If no semantic results available, do keyword-only
        if not sem_scores:
            return self._hydrate(
                sorted(kw_scores.items(), key=lambda x: x[1], reverse=True)[:top_k],
                "keyword",
                top_k,
                storage,
            )

        # Fuse scores
        all_ids = set(sem_scores.keys()) | set(kw_scores.keys())
        fused: list[tuple[str, float]] = []
        for sid in all_ids:
            score = w_sem * sem_scores.get(sid, 0.0) + w_kw * kw_scores.get(sid, 0.0)
            if score >= min_score:
                fused.append((sid, score))

        fused.sort(key=lambda x: x[1], reverse=True)
        return self._hydrate(fused[:top_k], "hybrid", top_k, storage)

    def _tag_search(self, query: str, top_k: int, storage: StorageEngine) -> list[SearchResult]:
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
        storage: StorageEngine,
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
                    matched_by=matched_by,
                )
            )

            if len(search_results) >= top_k:
                break

        return search_results
