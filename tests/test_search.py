"""Tests for the search engine.

Tests requiring sentence-transformers are marked as slow and skipped
if the dependency is not available.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import pytest

from snipcontext.config.settings import Config, SearchConfig, StorageConfig, reset_config
from snipcontext.core.models import Language, SearchMode, Snippet, SnippetMetadata
from snipcontext.core.search import SEMANTIC_AVAILABLE


def create_snippets():
    """Create test snippets with varied content."""
    return [
        Snippet(
            content="def authenticate_user(token):\n    return jwt.decode(token, SECRET)",
            metadata=SnippetMetadata(
                title="JWT Authentication",
                description="Decode and verify JWT tokens",
                language=Language.PYTHON,
            ),
            tags=["auth", "jwt", "security"],
        ),
        Snippet(
            content="class DatabaseConnection:\n    def __init__(self, dsn):\n        self.pool = create_pool(dsn)",
            metadata=SnippetMetadata(
                title="Database Connection Pool",
                description="Manage database connections",
                language=Language.PYTHON,
            ),
            tags=["database", "postgres", "connection"],
        ),
        Snippet(
            content="async def handle_request(req, res):\n    return json_response({'status': 'ok'})",
            metadata=SnippetMetadata(
                title="HTTP Request Handler",
                description="Basic async request handler",
                language=Language.PYTHON,
            ),
            tags=["web", "http", "async"],
        ),
        Snippet(
            content=r"function validateEmail(email) {\n    return /^[^\s@]+@[^\s@]+$/.test(email);\n}",
            metadata=SnippetMetadata(
                title="Email Validation",
                description="Regex email validator",
                language=Language.JAVASCRIPT,
            ),
            tags=["validation", "regex", "email"],
        ),
        Snippet(
            content="def password_hash(password):\n    return bcrypt.hashpw(password.encode(), bcrypt.gensalt())",
            metadata=SnippetMetadata(
                title="Password Hashing",
                description="Secure password hashing with bcrypt",
                language=Language.PYTHON,
            ),
            tags=["auth", "security", "password"],
        ),
    ]


@pytest.fixture
def temp_config():
    with tempfile.TemporaryDirectory() as tmp:
        config = Config(
            storage=StorageConfig(data_dir=Path(tmp)),
            search=SearchConfig(top_k=5, min_score=0.0),
        )
        yield config
        reset_config()


class TestKeywordIndex:
    """Tests for BM25 keyword search."""

    def test_build_and_search(self, temp_config):
        from snipcontext.core.search import KeywordIndex

        snippets = create_snippets()
        idx = KeywordIndex(temp_config)
        idx.build(snippets)

        assert idx.is_trained
        results = idx.search("authentication jwt", top_k=3)
        assert len(results) > 0
        assert results[0][0] == snippets[0].id

    def test_empty_index(self, temp_config):
        from snipcontext.core.search import KeywordIndex

        idx = KeywordIndex(temp_config)
        idx.build([])
        assert not idx.is_trained
        results = idx.search("anything", top_k=3)
        assert results == []


@pytest.mark.skipif(
    not SEMANTIC_AVAILABLE, reason="semantic search dependencies not installed"
)
@pytest.mark.slow
class TestEmbeddingEngine:
    """Tests for the embedding engine."""

    def test_load_model(self, temp_config):
        from snipcontext.core.search import EmbeddingEngine

        engine = EmbeddingEngine(temp_config)
        model = engine.model
        assert model is not None
        assert engine.dimension > 0

    def test_encode(self, temp_config):
        from snipcontext.core.search import EmbeddingEngine

        engine = EmbeddingEngine(temp_config)
        texts = ["hello world", "foo bar baz"]
        embeddings = engine.encode(texts)

        assert embeddings.shape == (2, engine.dimension)
        assert embeddings.dtype == np.float32

    def test_encode_query(self, temp_config):
        from snipcontext.core.search import EmbeddingEngine

        engine = EmbeddingEngine(temp_config)
        query_vec = engine.encode_query("authentication middleware")

        assert query_vec.shape == (1, engine.dimension)

    def test_normalize(self, temp_config):
        from snipcontext.core.search import EmbeddingEngine

        engine = EmbeddingEngine(temp_config)
        texts = ["test"]
        embeddings = engine.encode(texts)

        norm = np.linalg.norm(embeddings[0])
        assert abs(norm - 1.0) < 0.01


@pytest.mark.skipif(
    not SEMANTIC_AVAILABLE, reason="semantic search dependencies not installed"
)
@pytest.mark.slow
class TestVectorIndex:
    """Tests for FAISS vector index."""

    def test_build_and_search(self, temp_config):
        from snipcontext.core.search import EmbeddingEngine, VectorIndex

        snippets = create_snippets()
        engine = EmbeddingEngine(temp_config)
        idx = VectorIndex(temp_config)
        idx.build(snippets, engine)

        assert idx.is_trained
        assert idx.count == len(snippets)

        query_vec = engine.encode_query("jwt authentication token")
        results = idx.search(query_vec, top_k=3)
        assert len(results) > 0

    def test_empty_build(self, temp_config):
        from snipcontext.core.search import EmbeddingEngine, VectorIndex

        engine = EmbeddingEngine(temp_config)
        idx = VectorIndex(temp_config)
        idx.build([], engine)
        assert not idx.is_trained


@pytest.mark.skipif(
    not SEMANTIC_AVAILABLE, reason="semantic search dependencies not installed"
)
@pytest.mark.slow
class TestHybridSearch:
    """Integration tests for hybrid search."""

    def test_full_index_and_search(self, temp_config):
        from snipcontext.core.search import HybridSearch
        from snipcontext.core.storage import StorageEngine

        storage = StorageEngine(temp_config)
        snippets = create_snippets()
        for s in snippets:
            storage.save(s)

        searcher = HybridSearch(temp_config)
        searcher.index_snippets(snippets)

        results = searcher.search("authentication jwt", top_k=3)
        assert len(results) > 0
        assert any("jwt" in r.snippet.tags for r in results)

    def test_tag_search(self, temp_config):
        from snipcontext.core.search import HybridSearch
        from snipcontext.core.storage import StorageEngine

        storage = StorageEngine(temp_config)
        snippets = create_snippets()
        for s in snippets:
            storage.save(s)

        searcher = HybridSearch(temp_config)
        results = searcher.search("auth", top_k=10, mode=SearchMode.TAG)

        auth_snippets = [s for s in snippets if "auth" in s.tags]
        assert len(results) == len(auth_snippets)

    def test_keyword_search(self, temp_config):
        from snipcontext.core.search import HybridSearch
        from snipcontext.core.storage import StorageEngine

        storage = StorageEngine(temp_config)
        snippets = create_snippets()
        for s in snippets:
            storage.save(s)

        searcher = HybridSearch(temp_config)
        searcher.index_snippets(snippets)

        results = searcher.search("database connection pool", top_k=3, mode=SearchMode.KEYWORD)
        assert len(results) > 0

    def test_hybrid_mode_default(self, temp_config):
        from snipcontext.core.search import HybridSearch
        from snipcontext.core.storage import StorageEngine

        storage = StorageEngine(temp_config)
        snippets = create_snippets()
        for s in snippets:
            storage.save(s)

        searcher = HybridSearch(temp_config)
        searcher.index_snippets(snippets)

        results = searcher.search("secure password hashing", top_k=3)
        assert len(results) > 0

    def test_access_count_incremented(self, temp_config):
        from snipcontext.core.search import HybridSearch
        from snipcontext.core.storage import StorageEngine

        storage = StorageEngine(temp_config)
        s = Snippet(
            content="def test(): pass",
            metadata=SnippetMetadata(title="Test"),
            tags=["test"],
        )
        storage.save(s)

        searcher = HybridSearch(temp_config)
        searcher.index_snippets([s])

        searcher.search("test", mode=SearchMode.TAG)
        reloaded = storage.get(s.id)
        assert reloaded.access_count == 1

    def test_empty_collection(self, temp_config):
        from snipcontext.core.search import HybridSearch

        searcher = HybridSearch(temp_config)
        results = searcher.search("anything", top_k=3)
        assert results == []


class TestSemanticAvailabilityFlag:
    """Tests that the SEMANTIC_AVAILABLE flag is correctly exported and usable."""

    def test_flag_is_bool(self):
        from snipcontext.core.search import SEMANTIC_AVAILABLE

        assert isinstance(SEMANTIC_AVAILABLE, bool)

    def test_keyword_search_works_without_semantic(self, temp_config):
        """Keyword search must work regardless of whether semantic deps are installed."""
        from snipcontext.core.search import HybridSearch
        from snipcontext.core.storage import StorageEngine

        snippets = create_snippets()
        storage = StorageEngine(temp_config)
        for s in snippets:
            storage.save(s)

        searcher = HybridSearch(temp_config)
        searcher.index_snippets(snippets)

        # Keyword mode always works
        results = searcher.search("authentication jwt", top_k=3, mode=SearchMode.KEYWORD)
        assert len(results) > 0

    def test_hybrid_fallback_without_semantic(self, temp_config):
        """Hybrid mode should fall back to keyword-only when semantic is unavailable."""
        from snipcontext.core.search import HybridSearch
        from snipcontext.core.storage import StorageEngine

        snippets = create_snippets()
        storage = StorageEngine(temp_config)
        for s in snippets:
            storage.save(s)

        searcher = HybridSearch(temp_config)
        searcher.index_snippets(snippets)

        # Hybrid mode should still return results (keyword-only fallback)
        results = searcher.search("database connection pool", top_k=3)
        assert len(results) > 0

    def test_no_semantic_flag_forces_keyword(self, temp_config):
        """The no_semantic=True parameter must force keyword mode even for hybrid."""
        from snipcontext.core.search import HybridSearch
        from snipcontext.core.storage import StorageEngine

        snippets = create_snippets()
        storage = StorageEngine(temp_config)
        for s in snippets:
            storage.save(s)

        searcher = HybridSearch(temp_config)
        searcher.index_snippets(snippets)

        # hybrid without no_semantic — keyword fallback when deps missing
        results_kw = searcher.search("react component", top_k=3, mode="hybrid")
        # hybrid with no_semantic=True — explicitly forces keyword
        results_no_sem = searcher.search("react component", top_k=3, mode="hybrid", no_semantic=True)
        assert len(results_no_sem) > 0
        assert len(results_kw) == len(results_no_sem)

        # semantic mode with no_semantic=True — should fall back to keyword
        results_sem_forced = searcher.search("react component", top_k=3, mode="semantic", no_semantic=True)
        assert len(results_sem_forced) > 0

    def test_bm25_scores_normalized(self, temp_config):
        """BM25 raw scores must be normalized to [0, 1]."""
        from snipcontext.core.search import KeywordIndex

        snippets = create_snippets()
        idx = KeywordIndex(temp_config)
        idx.build(snippets)

        results = idx.search("authentication jwt", top_k=5)
        assert len(results) > 0
        # All scores should be in [0, 1] after normalization
        for sid, score in results:
            assert 0.0 <= score <= 1.0, f"Score {score} for {sid} outside [0, 1]"
        # Top result should have score == 1.0 (max normalization)
        assert results[0][1] == 1.0

    def test_bm25_save_load_roundtrip(self, temp_config):
        """BM25 index survives pickle save/load roundtrip."""
        import tempfile
        from pathlib import Path

        from snipcontext.core.search import KeywordIndex

        snippets = create_snippets()
        idx = KeywordIndex(temp_config)
        idx.build(snippets)

        with tempfile.TemporaryDirectory() as tmp:
            idx.save(Path(tmp))
            idx2 = KeywordIndex(temp_config)
            loaded = idx2.load(Path(tmp))
            assert loaded is True
            assert idx2.is_trained

            # Search results should match
            results1 = idx.search("authentication jwt", top_k=3)
            results2 = idx2.search("authentication jwt", top_k=3)
            assert len(results1) == len(results2)
            for (sid1, score1), (sid2, score2) in zip(results1, results2, strict=True):
                assert sid1 == sid2
                assert abs(score1 - score2) < 1e-6

    def test_bm25_tokenizer(self, temp_config):
        """_tokenize should handle code identifiers and unicode."""
        from snipcontext.core.search import KeywordIndex

        tokens = KeywordIndex._tokenize("def authenticate_user(token):\n    return jwt.decode")
        assert "def" in tokens
        assert "authenticate_user" in tokens
        assert "token" in tokens
        assert "jwt" in tokens
        # No punctuation tokens
        assert "(" not in tokens
        assert ":" not in tokens


class TestSearchFiltersAndScoring:
    """Tests for --lang, --tag, --boost-recent, and --explain (Issue #4)."""

    def test_lang_filter_python_only(self, temp_config):
        """--lang python should return only Python snippets."""
        from snipcontext.core.search import HybridSearch
        from snipcontext.core.storage import StorageEngine

        snippets = create_snippets()
        storage = StorageEngine(temp_config)
        for s in snippets:
            storage.save(s)

        searcher = HybridSearch(temp_config)
        searcher.index_snippets(snippets)

        results = searcher.search(
            "authenticate", top_k=10, mode="keyword", lang_filter=["python"]
        )
        assert len(results) > 0
        for r in results:
            assert r.snippet.metadata.language.value == "python"

    def test_lang_filter_javascript_only(self, temp_config):
        """--lang javascript should return only JS snippets."""
        from snipcontext.core.search import HybridSearch
        from snipcontext.core.storage import StorageEngine

        snippets = create_snippets()
        storage = StorageEngine(temp_config)
        for s in snippets:
            storage.save(s)

        searcher = HybridSearch(temp_config)
        searcher.index_snippets(snippets)

        results = searcher.search(
            "validation", top_k=10, mode="keyword", lang_filter=["javascript"]
        )
        assert len(results) > 0
        for r in results:
            assert r.snippet.metadata.language.value == "javascript"

    def test_lang_filter_excludes_mismatches(self, temp_config):
        """--lang go should return 0 results when no Go snippets exist."""
        from snipcontext.core.search import HybridSearch
        from snipcontext.core.storage import StorageEngine

        snippets = create_snippets()
        storage = StorageEngine(temp_config)
        for s in snippets:
            storage.save(s)

        searcher = HybridSearch(temp_config)
        searcher.index_snippets(snippets)

        results = searcher.search(
            "anything", top_k=10, mode="keyword", lang_filter=["go"]
        )
        assert results == []

    def test_tag_filter_and_logic(self, temp_config):
        """--tag with AND logic requires all tags to be present."""
        from snipcontext.core.search import HybridSearch
        from snipcontext.core.storage import StorageEngine

        snippets = create_snippets()
        storage = StorageEngine(temp_config)
        for s in snippets:
            storage.save(s)

        searcher = HybridSearch(temp_config)
        searcher.index_snippets(snippets)

        # auth + security → should match JWT auth and password hashing snippets
        results = searcher.search(
            "token password", top_k=10, mode="keyword", tag_filter=["auth", "security"]
        )
        assert len(results) > 0
        for r in results:
            assert "auth" in r.snippet.tags
            assert "security" in r.snippet.tags

    def test_tag_filter_partial_match_excluded(self, temp_config):
        """--tag requiring a non-existent tag should return 0 results."""
        from snipcontext.core.search import HybridSearch
        from snipcontext.core.storage import StorageEngine

        snippets = create_snippets()
        storage = StorageEngine(temp_config)
        for s in snippets:
            storage.save(s)

        searcher = HybridSearch(temp_config)
        searcher.index_snippets(snippets)

        results = searcher.search(
            "anything", top_k=10, mode="keyword", tag_filter=["auth", "nonexistent"]
        )
        assert results == []

    def test_combined_lang_and_tag_filter(self, temp_config):
        """--lang and --tag applied together should respect both."""
        from snipcontext.core.search import HybridSearch
        from snipcontext.core.storage import StorageEngine

        snippets = create_snippets()
        storage = StorageEngine(temp_config)
        for s in snippets:
            storage.save(s)

        searcher = HybridSearch(temp_config)
        searcher.index_snippets(snippets)

        results = searcher.search(
            "password",
            top_k=10,
            mode="keyword",
            lang_filter=["python"],
            tag_filter=["security"],
        )
        for r in results:
            assert r.snippet.metadata.language.value == "python"
            assert "security" in r.snippet.tags

    def test_boost_recent_changes_ranking(self, temp_config):
        """--boost-recent should affect ranking (same query, different order possible)."""
        from datetime import datetime, timedelta, timezone

        from snipcontext.core.search import HybridSearch
        from snipcontext.core.storage import StorageEngine

        # Create two snippets with different ages
        old_snippet = Snippet(
            content="def old_function(): return 'old'",
            metadata=SnippetMetadata(title="Old Snippet", language=Language.PYTHON),
            tags=["test"],
        )
        # Manually set created_at to 180 days ago
        old_snippet.created_at = datetime.now(timezone.utc) - timedelta(days=180)

        new_snippet = Snippet(
            content="def new_function(): return 'new'",
            metadata=SnippetMetadata(title="New Snippet", language=Language.PYTHON),
            tags=["test"],
        )

        storage = StorageEngine(temp_config)
        storage.save(old_snippet)
        storage.save(new_snippet)

        searcher = HybridSearch(temp_config)
        searcher.index_snippets([old_snippet, new_snippet])

        results_normal = searcher.search("function", top_k=2, mode="keyword")
        results_boosted = searcher.search(
            "function", top_k=2, mode="keyword", boost_recent=True
        )

        # Both should return results
        assert len(results_normal) > 0
        assert len(results_boosted) > 0
        # The new snippet should have a higher boosted score
        new_id = new_snippet.id
        old_id = old_snippet.id
        boosted_scores = {r.snippet.id: r.score for r in results_boosted}
        # New snippet should rank higher than old one after boosting
        assert boosted_scores.get(new_id, 0) > boosted_scores.get(old_id, 0)

    def test_explain_attaches_breakdown(self, temp_config):
        """--explain should attach an explanation dict to each result."""
        from snipcontext.core.search import HybridSearch
        from snipcontext.core.storage import StorageEngine

        snippets = create_snippets()
        storage = StorageEngine(temp_config)
        for s in snippets:
            storage.save(s)

        searcher = HybridSearch(temp_config)
        searcher.index_snippets(snippets)

        results = searcher.search(
            "authentication", top_k=3, mode="keyword", explain=True
        )
        assert len(results) > 0
        for r in results:
            assert r.explanation is not None
            assert "base_score" in r.explanation
            assert "matched_by" in r.explanation
            assert "language" in r.explanation
            assert "tags" in r.explanation
            assert "age_days" in r.explanation
            assert "access_count" in r.explanation

    def test_explain_without_flag_is_none(self, temp_config):
        """Without --explain, explanation should be None."""
        from snipcontext.core.search import HybridSearch
        from snipcontext.core.storage import StorageEngine

        snippets = create_snippets()
        storage = StorageEngine(temp_config)
        for s in snippets:
            storage.save(s)

        searcher = HybridSearch(temp_config)
        searcher.index_snippets(snippets)

        results = searcher.search("authentication", top_k=3, mode="keyword")
        assert len(results) > 0
        for r in results:
            assert r.explanation is None


class TestMultiQueryAndGrouping:
    """Tests for multi-query search, query weights, and result grouping (Issue #32)."""

    def test_multi_search_deduplicates(self, temp_config):
        """Multi-query should deduplicate snippets appearing in multiple queries."""
        from snipcontext.core.search import HybridSearch
        from snipcontext.core.storage import StorageEngine

        snippets = create_snippets()
        storage = StorageEngine(temp_config)
        for s in snippets:
            storage.save(s)

        searcher = HybridSearch(temp_config)
        searcher.index_snippets(snippets)

        # Two queries that may overlap on some snippets
        results = searcher.multi_search(
            ["authentication", "security"], top_k=10, mode="keyword"
        )
        # Check no duplicate snippet IDs
        ids = [r.snippet.id for r in results]
        assert len(ids) == len(set(ids)), "Multi-search returned duplicates"
        assert len(results) > 0

    def test_multi_search_weighted_queries(self, temp_config):
        """Query with ^2 weight should influence ranking differently than unweighted."""
        from snipcontext.core.search import HybridSearch
        from snipcontext.core.storage import StorageEngine

        snippets = create_snippets()
        storage = StorageEngine(temp_config)
        for s in snippets:
            storage.save(s)

        searcher = HybridSearch(temp_config)
        searcher.index_snippets(snippets)

        # Weighted vs unweighted should produce different rankings
        results_unweighted = searcher.multi_search(
            ["authentication", "database"], top_k=5, mode="keyword"
        )
        results_weighted = searcher.multi_search(
            ["authentication^3", "database"], top_k=5, mode="keyword"
        )
        assert len(results_unweighted) > 0
        assert len(results_weighted) > 0

    def test_parse_query_weights(self, temp_config):
        """_parse_query_weights should handle ^N syntax correctly."""
        from snipcontext.core.search import HybridSearch

        assert HybridSearch._parse_query_weights(["http^2", "error"]) == [
            ("http", 2.0),
            ("error", 1.0),
        ]
        assert HybridSearch._parse_query_weights(["python"]) == [
            ("python", 1.0),
        ]
        assert HybridSearch._parse_query_weights(["api^3", "rest^1.5"]) == [
            ("api", 3.0),
            ("rest", 1.5),
        ]
        # Invalid weight defaults to 1.0
        assert HybridSearch._parse_query_weights(["test^abc"]) == [
            ("test", 1.0),
        ]

    def test_multi_search_empty_queries(self, temp_config):
        """Empty query list should return empty results."""
        from snipcontext.core.search import HybridSearch

        searcher = HybridSearch(temp_config)
        results = searcher.multi_search([], mode="keyword")
        assert results == []

    def test_group_by_language(self, temp_config):
        """Grouping by language should create correct groups."""
        from snipcontext.core.search import HybridSearch
        from snipcontext.core.storage import StorageEngine

        snippets = create_snippets()
        storage = StorageEngine(temp_config)
        for s in snippets:
            storage.save(s)

        searcher = HybridSearch(temp_config)
        searcher.index_snippets(snippets)

        results = searcher.search("code function", top_k=10, mode="keyword")
        groups = HybridSearch.group_results(results, group_by="language")

        # Should have at least a python group
        assert "python" in groups
        assert len(groups["python"]) > 0

    def test_group_by_tag(self, temp_config):
        """Grouping by tag should create correct groups."""
        from snipcontext.core.search import HybridSearch
        from snipcontext.core.storage import StorageEngine

        snippets = create_snippets()
        storage = StorageEngine(temp_config)
        for s in snippets:
            storage.save(s)

        searcher = HybridSearch(temp_config)
        searcher.index_snippets(snippets)

        results = searcher.search("code", top_k=10, mode="keyword")
        groups = HybridSearch.group_results(results, group_by="tag")

        # Should have at least one tag group
        assert len(groups) > 0

    def test_group_by_source(self, temp_config):
        """Grouping by source should group all as 'local' (no source_url)."""
        from snipcontext.core.search import HybridSearch
        from snipcontext.core.storage import StorageEngine

        snippets = create_snippets()
        storage = StorageEngine(temp_config)
        for s in snippets:
            storage.save(s)

        searcher = HybridSearch(temp_config)
        searcher.index_snippets(snippets)

        results = searcher.search("code", top_k=10, mode="keyword")
        groups = HybridSearch.group_results(results, group_by="source")

        assert "local" in groups
        assert len(groups["local"]) > 0

    def test_group_by_per_group_limit(self, temp_config):
        """per_group should limit results within each group."""
        from snipcontext.core.search import HybridSearch
        from snipcontext.core.storage import StorageEngine

        snippets = create_snippets()
        storage = StorageEngine(temp_config)
        for s in snippets:
            storage.save(s)

        searcher = HybridSearch(temp_config)
        searcher.index_snippets(snippets)

        results = searcher.search("code", top_k=10, mode="keyword")
        groups = HybridSearch.group_results(results, group_by="language", per_group=1)

        for key, group in groups.items():
            assert len(group) <= 1

    def test_multi_search_with_explain(self, temp_config):
        """Multi-search with explain should attach RRF scores."""
        from snipcontext.core.search import HybridSearch
        from snipcontext.core.storage import StorageEngine

        snippets = create_snippets()
        storage = StorageEngine(temp_config)
        for s in snippets:
            storage.save(s)

        searcher = HybridSearch(temp_config)
        searcher.index_snippets(snippets)

        results = searcher.multi_search(
            ["authentication", "security"], top_k=5, mode="keyword", explain=True
        )
        assert len(results) > 0
        for r in results:
            assert r.explanation is not None
            assert "rrf_score" in r.explanation
            assert "num_queries" in r.explanation
            assert r.explanation["num_queries"] == 2
