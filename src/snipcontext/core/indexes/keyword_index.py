"""BM25 (Okapi BM25) keyword search index for SnipContext."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

from snipcontext.config.settings import Config, get_config
from snipcontext.core.models import Snippet

if TYPE_CHECKING:
    from pathlib import Path

    from rank_bm25 import BM25Okapi

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Keyword index (BM25)
# ---------------------------------------------------------------------------


class KeywordIndex:
    """BM25 (Okapi BM25) keyword search index.

    Provides fast exact and fuzzy text matching for snippet content,
    titles, descriptions, and tags.  BM25 handles term-frequency saturation
    and document-length normalization better than TF-IDF for short texts
    such as code snippets.
    """

    BM25_AVAILABLE: bool = True
    """Whether rank_bm25 (BM25Okapi) is importable.  When False, keyword search
    falls back to a simple token-overlap scorer."""

    _bm25_cache: BM25Okapi | None = None
    """Cached BM25Okapi instance, set by :meth:`build` when available."""

    def __init__(self, config: Config | None = None) -> None:
        self._config = config or get_config()
        self._bm25: BM25Okapi | None = None
        self._corpus: list[list[str]] | None = None
        self._id_map: list[str] = []
        self._texts: list[str] = []

    @property
    def is_trained(self) -> bool:
        """Return True if the index has corpus data.

        The original implementation required both a BM25 object and a corpus.
        When ``rank_bm25`` is unavailable we still want the index to be usable,
        so we consider the index trained as long as ``_corpus`` is populated.
        """
        return self._corpus is not None

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """Lowercase word-tokenization for BM25 input.

        Uses a simple regex split which handles code identifiers,
        punctuation boundaries, and unicode word characters.
        """
        import re

        return re.findall(r"\w+", text.lower())

    def build(self, snippets: list[Snippet]) -> None:
        """Build the BM25 index from snippets.

        When ``rank_bm25`` is available, creates a full BM25Okapi index.
        When it is not, stores the corpus and texts for simple token-overlap
        scoring in :meth:`search`.
        """
        try:
            from rank_bm25 import BM25Okapi
        except ImportError:
            logger.warning(
                "rank_bm25 not installed; falling back to simple keyword scoring. "
                "Install with: pip install snipcontext[full]",
            )
            # Still store corpus + texts for fallback search
            if not snippets:
                self._bm25 = None
                self._corpus = None
                self._id_map = []
                self._texts = []
                return

            texts = [s.to_search_text() for s in snippets]
            self._texts = texts
            self._corpus = [self._tokenize(t) for t in texts]
            self._id_map = [s.id for s in snippets]
            self._bm25 = None
            return

        if not snippets:
            self._bm25 = None
            self._corpus = None
            self._id_map = []
            self._texts = []
            return

        texts = [s.to_search_text() for s in snippets]
        self._texts = texts  # Store for fuzzy matching
        self._corpus = [self._tokenize(t) for t in texts]
        self._bm25 = BM25Okapi(self._corpus)
        self._id_map = [s.id for s in snippets]

        logger.info(
            "Built keyword index: %d docs (BM25Okapi)",
            len(snippets),
        )

    def search(
        self,
        query: str,
        top_k: int,
        min_score: float = 0.0,
        fuzzy: bool = False,
    ) -> list[tuple[str, float]]:
        """Search by keyword relevance using BM25 scoring.

        When BM25 (rank_bm25) is available, uses BM25Okapi scoring.  When it is
        not, falls back to simple token-overlap counting.

        BM25 scores are unbounded positive floats.  They are normalized to
        the [0, 1] range by dividing by the maximum score in the current
        result set so that they are compatible with ``min_score`` thresholds
        and hybrid-fusion score ranges.

        Args:
            query: The search query string.
            top_k: Maximum number of results.
            min_score: Minimum relevance score (0.0 to 1.0).
            fuzzy: Enable fuzzy matching with rapidfuzz.

        Returns:
            List of (snippet_id, score) tuples sorted by relevance.
        """
        if not self.is_trained:
            return []
        tokens = self._tokenize(query)
        # Use BM25 if available, otherwise fallback to simple token overlap scoring.
        if self._bm25 is not None:
            raw_scores = self._bm25.get_scores(tokens)
            max_score = float(raw_scores.max())
            if max_score > 0:
                scores = raw_scores / max_score
            else:
                scores = raw_scores.astype(np.float64)
        else:
            # Simple token overlap scoring as fallback.
            scores = np.zeros(len(self._corpus or []), dtype=np.float64)
            for i, doc_tokens in enumerate(self._corpus or []):
                overlap = len(set(tokens) & set(doc_tokens))
                if overlap > 0:
                    denom = (
                        max(len(tokens), len(doc_tokens)) if (len(tokens) or len(doc_tokens)) else 1
                    )
                    scores[i] = overlap / denom
            if scores.max() > 0:
                scores = scores / scores.max()

        if fuzzy:
            # Augment with fuzzy matching against original texts
            try:
                fuzzy_scores = self._fuzzy_search(query, top_k, min_score)
                for idx, f_score in fuzzy_scores:
                    bm25_norm = float(scores[idx]) if idx < len(scores) else 0.0
                    blended = 0.7 * bm25_norm + 0.3 * f_score
                    scores[idx] = blended
            except ImportError:
                pass  # rapidfuzz not available, skip fuzzy matching

        # Get top-k indices
        if top_k >= len(scores):
            top_indices = np.argsort(scores)[::-1]
        else:
            top_indices = np.argpartition(scores, -top_k)[-top_k:]
            top_indices = top_indices[np.argsort(scores[top_indices])[::-1]]

        results: list[tuple[str, float]] = []
        for idx in top_indices:
            score = float(scores[idx])
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
        """Save the keyword index to disk as JSON."""
        if not self.is_trained:
            return
        path.mkdir(parents=True, exist_ok=True)
        payload = {
            "id_map": self._id_map,
            "corpus": self._corpus,
            "texts": self._texts,
        }
        (path / "keyword_index.json").write_text(json.dumps(payload))
        logger.debug("Saved keyword index to %s", path)

    def load(self, path: Path) -> bool:
        """Load the keyword index from disk.

        When rank_bm25 is available, the BM25Okapi index is rebuilt from the
        stored corpus.  When it is not, the corpus and texts are still loaded
        so that the simple token-overlap fallback in :meth:`search` can work.
        """
        index_file = path / "keyword_index.json"
        legacy_file = path / "keyword_index.pkl"
        if not index_file.exists() and legacy_file.exists():
            try:
                legacy_file.unlink()
            except OSError:
                pass
        if not index_file.exists():
            logger.debug("Keyword index file not found at %s", path)
            return False
        try:
            payload = json.loads(index_file.read_text(encoding="utf-8"))
            self._id_map = [str(i) for i in payload.get("id_map", [])]
            self._corpus = [list(map(str, doc)) for doc in payload.get("corpus", [])]
            self._texts = [str(t) for t in payload.get("texts", [])]
            if self._corpus and len(self._id_map) != len(self._corpus):
                logger.warning(
                    "Keyword index ID map length mismatch: %d IDs vs %d docs",
                    len(self._id_map),
                    len(self._corpus),
                )
                return False
            if self._corpus:
                try:
                    from rank_bm25 import BM25Okapi

                    self._bm25 = BM25Okapi(self._corpus)
                except ImportError:
                    logger.warning(
                        "rank_bm25 not available; loading keyword index in "
                        "fallback mode (token-overlap only).",
                    )
                    self._bm25 = None
            else:
                self._bm25 = None
                self._corpus = None
            logger.debug("Loaded keyword index from %s", path)
            return True
        except Exception as exc:
            logger.warning("Failed to load keyword index from %s: %s", path, exc)
            try:
                if index_file.exists():
                    index_file.unlink()
            except OSError as cleanup_err:
                logger.warning(
                    "Failed to clean up corrupted keyword index file: %s",
                    cleanup_err,
                )
            return False
