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
    """Tests for TF-IDF keyword search."""

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
