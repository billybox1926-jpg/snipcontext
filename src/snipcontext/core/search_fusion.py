"""Search orchestration for SnipContext.

Implements the two top-level search strategies built on top of the
embedding engine and the vector/keyword indices:

1. ``SemanticSearch`` — pure dense vector similarity search.
2. ``HybridSearch`` — weighted fusion of semantic + keyword scores, plus
   query/ranking features: multi-query search, filtering, recency boost,
   result grouping, and scoring explanations.

All processing happens locally — no data leaves the machine.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Literal

import numpy as np

from snipcontext.config.settings import Config, get_config
from snipcontext.core.embeddings import SEMANTIC_AVAILABLE, EmbeddingEngine
from snipcontext.core.indexes.keyword_index import KeywordIndex
from snipcontext.core.indexes.vector_index import VectorIndex
from snipcontext.core.models import SearchMode, SearchResult, Snippet
from snipcontext.core.storage import StorageError

if TYPE_CHECKING:
    from snipcontext.core.storage import StorageEngine

logger = logging.getLogger(__name__)

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
        matched_by: Literal["semantic", "keyword", "hybrid", "tag"],
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
            except StorageError:
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
        self._embed_cache: dict[str, np.ndarray] = {}
        self._keyword_dirty: bool = False

        if not SEMANTIC_AVAILABLE:
            logger.warning(
                "Semantic search dependencies (sentence-transformers, faiss-cpu) are not "
                "installed. Search will use keyword-only mode. For full hybrid search, "
                "install with: pip install snipcontext[semantic]"
            )

    def load_indices(self) -> tuple[bool, bool]:
        """Load existing search indices from disk if available.

        Returns:
            Tuple of (semantic_loaded, keyword_loaded).
        """
        semantic_loaded = self.vector_index.load(self._config.index_path)
        keyword_loaded = self.keyword_index.load(self._config.index_path)
        if semantic_loaded and keyword_loaded:
            self._keyword_dirty = False
        return semantic_loaded, keyword_loaded

    @property
    def indices_ready(self) -> bool:
        """Return True if the required search indices are trained.

        When semantic deps are available, both semantic and keyword indices
        must be ready.  When they are missing, only the keyword index is
        required.  Attempts to load from disk if not currently trained.
        """
        if self.keyword_index.is_trained:
            if SEMANTIC_AVAILABLE:
                return self.vector_index.is_trained
            return True
        # Try loading from disk
        sem_loaded, kw_loaded = self.load_indices()
        if SEMANTIC_AVAILABLE:
            return sem_loaded and kw_loaded
        return kw_loaded

    def index_snippets(self, snippets: list[Snippet]) -> None:
        """Build both semantic and keyword indices."""
        semantic_loaded, keyword_loaded = self.load_indices()

        if semantic_loaded and keyword_loaded:
            logger.debug("Loaded existing search indices from %s", self._config.index_path)
            if not snippets:
                return

            # Rebuild semantic index if deps available
            if SEMANTIC_AVAILABLE:
                self.vector_index.build([s for s in snippets if not s.deleted], self.embedder)
                if not self.vector_index.is_trained:
                    raise RuntimeError("Vector index build failed after merging snippets")
                self.vector_index.save(self._config.index_path)

            self.keyword_index.build([s for s in snippets if not s.deleted])
            if not self.keyword_index.is_trained:
                raise RuntimeError("Keyword index build failed after merging snippets")

            self.keyword_index.save(self._config.index_path)
            self._keyword_dirty = False
            return

        self._build_indices_from_scratch(snippets)

    def _build_indices_from_scratch(self, snippets: list[Snippet]) -> None:
        active = [s for s in snippets if not getattr(s, "deleted", False)]
        logger.info("Rebuilding search indices (%d snippets)", len(active))

        semantic_ok = False
        try:
            self.vector_index.build(active, self.embedder)
            self.vector_index.save(self._config.index_path)
            semantic_ok = True
        except (ImportError, OSError) as exc:
            logger.warning("Semantic index build failed: %s", exc)
            logger.info("Falling back to keyword-only search")

        try:
            self.keyword_index.build(active)
            self.keyword_index.save(self._config.index_path)
        except Exception as exc:
            logger.error("Keyword index build failed: %s", exc)
            raise StorageError(
                f"Failed to build keyword index: {exc}",
                code="index_corrupted",
            ) from exc

        self._keyword_dirty = False

        if not semantic_ok:
            logger.info("Built keyword-only index (semantic unavailable)")
        else:
            logger.info("Built hybrid search indices (semantic + keyword)")

    def add_snippet(self, snippet: Snippet) -> None:
        """Incrementally add or update a single snippet in the index.

        Vector index is updated immediately (if semantic deps available).
        Keyword index is marked dirty and rebuilt lazily on next keyword/hybrid
        search or explicit save.
        """
        if SEMANTIC_AVAILABLE:
            self.vector_index.add_vector(snippet, self.embedder)
            self.vector_index.save(self._config.index_path)
        self._keyword_dirty = True

    def remove_snippet(self, snippet_id: str) -> None:
        """Remove a snippet from the vector index (if available) and mark keyword index dirty."""
        if SEMANTIC_AVAILABLE:
            self.vector_index.remove_vector(snippet_id)
            self.vector_index.save(self._config.index_path)
        self._keyword_dirty = True

    def rebuild_keyword_index(self, snippets: list[Snippet]) -> None:
        """Rebuild the keyword index from a full snippet list and clear dirty flag."""
        active = [s for s in snippets if not s.deleted]
        self.keyword_index.build(active)
        self.keyword_index.save(self._config.index_path)
        self._keyword_dirty = False

    def rebuild_incremental(self, snippets: list[Snippet]) -> None:
        """Rebuild indices from a snapshot, excluding soft-deleted snippets."""
        active = [snip for snip in snippets if not snip.deleted]
        self.index_snippets(active)

    def _ensure_keyword_index(self) -> None:
        """Rebuild keyword index if dirty before a keyword-dependent search."""
        if self._keyword_dirty:
            from snipcontext.core.storage import StorageEngine

            storage = StorageEngine(self._config)
            self.rebuild_keyword_index(storage.list_all())

    def search(
        self,
        query: str,
        top_k: int | None = None,
        mode: SearchMode | str | None = None,
        min_score: float | None = None,
        fuzzy: bool = False,
        no_semantic: bool = False,
        semantic_weight: float | None = None,
        keyword_weight: float | None = None,
        lang_filter: list[str] | None = None,
        tag_filter: list[str] | None = None,
        boost_recent: bool = False,
        explain: bool = False,
    ) -> list[SearchResult]:
        """Execute search using the specified or default strategy.

        Args:
            query: The search query string.
            top_k: Maximum number of results. Defaults to config.
            mode: Override search strategy. Defaults to config default_mode.
            min_score: Minimum relevance score threshold. Defaults to config.min_score.
            fuzzy: Enable fuzzy matching for keyword search.
            no_semantic: If True, force keyword-only mode even when semantic deps
                are available.
            semantic_weight: Override semantic fusion weight in hybrid mode.
                Must be in [0, 1]. Defaults to config value.
            keyword_weight: Override keyword fusion weight in hybrid mode.
                Must be in [0, 1]. Defaults to `1 - semantic_weight`.
            lang_filter: Only return snippets whose language is in this list.
            tag_filter: Only return snippets whose tags include ALL of these (AND).
            boost_recent: Add a recency bonus so newer snippets rank higher.
            explain: Attach scoring breakdown dict to each SearchResult.

        Returns:
            Ranked list of SearchResult objects.
        """
        from snipcontext.core.storage import StorageEngine

        top_k = top_k or self._config.search.top_k
        mode = SearchMode(mode or self._config.search.default_mode)
        min_score = min_score if min_score is not None else self._config.search.min_score
        storage = StorageEngine(self._config)

        if semantic_weight is not None:
            semantic_weight = max(0.0, min(1.0, semantic_weight))
        if keyword_weight is not None:
            keyword_weight = max(0.0, min(1.0, keyword_weight))
        if semantic_weight is not None and keyword_weight is None:
            keyword_weight = max(0.0, min(1.0, 1.0 - semantic_weight))
        elif keyword_weight is not None and semantic_weight is None:
            semantic_weight = max(0.0, min(1.0, 1.0 - keyword_weight))

        # Normalise filters
        lang_set: set[str] | None = None
        if lang_filter:
            lang_set = {item.strip().lower() for item in lang_filter}
        tag_set: set[str] | None = None
        if tag_filter:
            tag_set = {tag.strip().lower() for tag in tag_filter}

        if no_semantic and mode in (SearchMode.HYBRID, SearchMode.SEMANTIC):
            logger.debug("--no-semantic flag active, forcing keyword search")
            mode = SearchMode.KEYWORD

        if mode == SearchMode.TAG:
            results = self._tag_search(query, top_k, storage)
            if lang_set or tag_set:
                results = self._apply_filters(results, lang_set, tag_set)
            return results

        # Rebuild keyword index lazily if dirty
        if mode in (SearchMode.KEYWORD, SearchMode.HYBRID):
            self._ensure_keyword_index()

        if mode == SearchMode.KEYWORD:
            results = self._keyword_search(query, top_k, min_score, fuzzy, storage)
        elif mode == SearchMode.SEMANTIC:
            results = self._semantic_search(query, top_k, min_score, storage)
        else:
            results = self._hybrid_search(
                query,
                top_k,
                min_score,
                fuzzy,
                storage,
                semantic_weight=semantic_weight,
                keyword_weight=keyword_weight,
            )

        # Apply post-search filters
        if lang_set or tag_set:
            results = self._apply_filters(results, lang_set, tag_set)

        # Apply recency boost
        if boost_recent and results:
            results = self._apply_recency_boost(results)

        # Attach explanation
        if explain and results:
            results = self._attach_explanations(results, mode.value)

        return results

    def _semantic_search(
        self, query: str, top_k: int, min_score: float, storage: StorageEngine
    ) -> list[SearchResult]:
        """Pure semantic search path."""
        if not SEMANTIC_AVAILABLE:
            logger.warning(
                "Semantic search requested but dependencies are not installed. "
                "Falling back to keyword search. Install with: pip install snipcontext[semantic]"
            )
            return self._keyword_search(query, top_k, min_score, False, storage)

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
        semantic_weight: float | None = None,
        keyword_weight: float | None = None,
    ) -> list[SearchResult]:
        """Weighted fusion of semantic and keyword scores."""
        w_sem = (
            semantic_weight if semantic_weight is not None else self._config.search.semantic_weight
        )
        w_kw = keyword_weight if keyword_weight is not None else self._config.search.keyword_weight

        # Semantic results (if index available)
        sem_scores: dict[str, float] = {}
        if SEMANTIC_AVAILABLE and self.vector_index.is_trained:
            try:
                query_embedding = self.embedder.encode_query(query)
                sem_raw = self.vector_index.search(
                    query_embedding, top_k=top_k * 3, min_score=min_score
                )
                sem_scores = dict(sem_raw)
            except (ImportError, RuntimeError, OSError):
                logger.debug("Semantic search failed, falling back to keyword-only")

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

    @staticmethod
    def _apply_filters(
        results: list[SearchResult],
        lang_set: set[str] | None,
        tag_set: set[str] | None,
    ) -> list[SearchResult]:
        """Post-filter results by language and/or tags."""
        filtered: list[SearchResult] = []
        for r in results:
            s = r.snippet
            if lang_set and s.metadata.language.value.lower() not in lang_set:
                continue
            if tag_set and not tag_set.issubset(set(s.tags)):
                continue
            filtered.append(r)
        return filtered

    @staticmethod
    def _apply_recency_boost(results: list[SearchResult]) -> list[SearchResult]:
        """Re-rank results with a recency bonus.

        Uses exponential decay: ``bonus = exp(-days/90)`` so snippets from
        today get ~1.0 bonus, 90 days ago ~0.37, 180 days ~0.14.
        The bonus is blended 80/20 with the original score.
        """
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        recalculated: list[SearchResult] = []
        for r in results:
            s = r.snippet
            age_days = max(0.0, (now - s.created_at).total_seconds() / 86400)
            recency = float(np.exp(-age_days / 90.0))
            boosted = 0.8 * r.score + 0.2 * recency
            # Rebuild the SearchResult with the boosted score
            recalculated.append(
                SearchResult(
                    snippet=s,
                    score=min(boosted, 1.0),
                    matched_by=r.matched_by,
                    highlights=r.highlights,
                )
            )
        # Re-sort by boosted score
        recalculated.sort(key=lambda x: x.score, reverse=True)
        return recalculated

    @staticmethod
    def _attach_explanations(results: list[SearchResult], mode: str) -> list[SearchResult]:
        """Attach scoring breakdown dicts to each result."""
        from datetime import datetime, timezone

        explained: list[SearchResult] = []
        for r in results:
            s = r.snippet
            age_days = max(0.0, (datetime.now(timezone.utc) - s.created_at).total_seconds() / 86400)
            explanation: dict[str, float | str] = {
                "base_score": round(r.score, 4),
                "matched_by": mode,
                "language": s.metadata.language.value,
                "tags": ", ".join(s.tags) if s.tags else "(none)",
                "age_days": round(age_days, 1),
                "access_count": s.access_count,
            }
            explained.append(
                SearchResult(
                    snippet=s,
                    score=r.score,
                    matched_by=r.matched_by,
                    highlights=r.highlights,
                    explanation=explanation,
                )
            )
        return explained

    def _hydrate(
        self,
        raw_results: list[tuple[str, float]],
        matched_by: Literal["semantic", "keyword", "hybrid", "tag"],
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
            except StorageError:
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

    # -------------------------------------------------------------------
    # Multi-query search & result grouping
    # -------------------------------------------------------------------

    @staticmethod
    def _parse_query_weights(
        queries: list[str],
    ) -> list[tuple[str, float]]:
        """Parse ``query^weight`` syntax into (query, weight) pairs.

        Examples::

            ["http^2", "error"]       -> [("http", 2.0), ("error", 1.0)]
            ["python"]                -> [("python", 1.0)]
            ["api^3", "rest^1.5"]     -> [("api", 3.0), ("rest", 1.5)]
        """
        parsed: list[tuple[str, float]] = []
        for q in queries:
            if "^" in q:
                parts = q.rsplit("^", 1)
                try:
                    weight = float(parts[1])
                except ValueError:
                    weight = 1.0
                parsed.append((parts[0], weight))
            else:
                parsed.append((q, 1.0))
        return parsed

    def multi_search(
        self,
        queries: list[str],
        top_k: int | None = None,
        mode: SearchMode | str | None = None,
        min_score: float | None = None,
        fuzzy: bool = False,
        no_semantic: bool = False,
        semantic_weight: float | None = None,
        keyword_weight: float | None = None,
        lang_filter: list[str] | None = None,
        tag_filter: list[str] | None = None,
        boost_recent: bool = False,
        explain: bool = False,
    ) -> list[SearchResult]:
        """Run multiple queries, merge results with dedup and weighted scores.

        Each query is run independently via :meth:`search`.  Scores for the
        same snippet across queries are combined using a weighted reciprocal
        rank fusion (RRF).  The weight from ``query^N`` syntax multiplies
        the query's contribution.

        Args:
            queries: List of query strings (optionally with ``^weight`` suffix).
            top_k: Maximum number of results.
            mode: Search strategy.
            min_score: Minimum relevance score.
            fuzzy: Enable fuzzy matching.
            no_semantic: Force keyword-only mode.
            semantic_weight: Override semantic fusion weight for underlying searches.
            keyword_weight: Override keyword fusion weight for underlying searches.
            lang_filter: Filter by language.
            tag_filter: Filter by tags (AND).
            boost_recent: Weight newer snippets higher.
            explain: Attach scoring breakdown.

        Returns:
            Merged, deduped, ranked list of SearchResults.
        """
        if not queries:
            return []

        parsed = self._parse_query_weights(queries)
        top_k = top_k or self._config.search.top_k
        k = 60  # RRF constant

        # Collect per-query results
        per_query: list[list[SearchResult]] = []
        for query_text, _weight in parsed:
            results = self.search(
                query_text,
                top_k=top_k,
                mode=mode,
                min_score=min_score,
                fuzzy=fuzzy,
                no_semantic=no_semantic,
                semantic_weight=semantic_weight,
                keyword_weight=keyword_weight,
                explain=False,  # explanation added after merge
            )
            per_query.append(results)

        # Weighted Reciprocal Rank Fusion
        snippet_scores: dict[str, float] = {}
        snippet_map: dict[str, SearchResult] = {}

        for qi, results in enumerate(per_query):
            query_weight = parsed[qi][1]
            for rank, r in enumerate(results, start=1):
                sid = r.snippet.id
                rrf = query_weight / (k + rank)
                snippet_scores[sid] = snippet_scores.get(sid, 0.0) + rrf
                if sid not in snippet_map or r.score > snippet_map[sid].score:
                    snippet_map[sid] = r

        # Sort by combined RRF score (descending)
        sorted_ids = sorted(snippet_scores.items(), key=lambda x: x[1], reverse=True)

        # Rebuild SearchResults with fused score
        merged: list[SearchResult] = []
        for sid, rrf_score in sorted_ids[:top_k]:
            r = snippet_map[sid]
            merged.append(
                SearchResult(
                    snippet=r.snippet,
                    score=r.score,
                    matched_by=r.matched_by,
                    highlights=r.highlights,
                    explanation={
                        "rrf_score": round(rrf_score, 4),
                        "original_score": round(r.score, 4),
                        "matched_by": r.matched_by,
                        "num_queries": len(parsed),
                    }
                    if explain
                    else None,
                )
            )

        # Apply post-filters
        lang_set: set[str] | None = None
        if lang_filter:
            lang_set = {item.strip().lower() for item in lang_filter}
        tag_set: set[str] | None = None
        if tag_filter:
            tag_set = {tag.strip().lower() for tag in tag_filter}

        if lang_set or tag_set:
            merged = self._apply_filters(merged, lang_set, tag_set)

        if boost_recent and merged:
            merged = self._apply_recency_boost(merged)

        return merged

    @staticmethod
    def group_results(
        results: list[SearchResult],
        group_by: str,
        per_group: int = 3,
    ) -> dict[str, list[SearchResult]]:
        """Group search results by a snippet attribute.

        Args:
            results: Flat list of SearchResults.
            group_by: One of ``"language"``, ``"tag"``, ``"source"``.
            per_group: Maximum results per group.

        Returns:
            Dict mapping group key to list of SearchResults.
        """
        groups: dict[str, list[SearchResult]] = {}
        for r in results:
            s = r.snippet
            if group_by == "language":
                key = s.metadata.language.value
            elif group_by == "tag":
                key = s.tags[0] if s.tags else "untagged"
            elif group_by == "source":
                key = s.metadata.source_url or "local"
            else:
                key = "other"

            if key not in groups:
                groups[key] = []
            if len(groups[key]) < per_group:
                groups[key].append(r)

        def _group_score(items: list[SearchResult]) -> float:
            return sum(r.score for r in items)

        return dict(sorted(groups.items(), key=lambda x: _group_score(x[1]), reverse=True))
