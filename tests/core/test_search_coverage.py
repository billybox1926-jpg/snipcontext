"""Coverage-focused tests for src/snipcontext/core/search.py."""

from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np
import pytest

from snipcontext.config.settings import Config, SearchConfig, StorageConfig
from snipcontext.core.models import (
    Language,
    SearchMode,
    SearchResult,
    Snippet,
    SnippetMetadata,
)
from snipcontext.core.search import (
    EmbeddingEngine,
    HybridSearch,
    KeywordIndex,
    VectorIndex,
)


def _config(tmp_path):
    return Config(
        storage=StorageConfig(data_dir=tmp_path),
        search=SearchConfig(top_k=5, min_score=0.0),
    )


def _snippet(snippet_id: str = "s1") -> Snippet:
    return Snippet(
        id=snippet_id,
        content=f"content {snippet_id}",
        metadata=SnippetMetadata(
            title=f"Title {snippet_id}",
            language=Language.PYTHON,
        ),
        tags=[snippet_id],
    )


def _make_snippet_plain(
    snippet_id: str,
    language: Language = Language.PYTHON,
    tags: list[str] | None = None,
) -> Snippet:
    return Snippet(
        id=snippet_id,
        content=f"content {snippet_id}",
        metadata=SnippetMetadata(
            title=f"Title {snippet_id}",
            language=language,
        ),
        tags=tags or [],
    )


class TestEmbeddingEngineEdgeCases:
    """Cover EmbeddingEngine branches that are hard to hit with real deps."""

    def test_dimension_raises_when_semantic_unavailable(self, tmp_path, mocker):
        search_module = pytest.importorskip("snipcontext.core.search")
        original = search_module.SEMANTIC_AVAILABLE
        try:
            search_module.SEMANTIC_AVAILABLE = False
            engine = EmbeddingEngine(_config(tmp_path))
            with pytest.raises(ImportError):
                _ = engine.dimension
        finally:
            search_module.SEMANTIC_AVAILABLE = original

    def test_encode_empty_texts(self, tmp_path):
        engine = EmbeddingEngine(_config(tmp_path))
        model = MagicMock()
        model.get_sentence_embedding_dimension.return_value = 16
        engine._model = model
        out = engine.encode([])
        assert out.shape == (0, 16)

    def test_encode_query_shapes(self, tmp_path):
        engine = EmbeddingEngine(_config(tmp_path))
        model = MagicMock()
        model.encode.return_value = np.zeros((1, 16), dtype=np.float32)
        model.get_sentence_embedding_dimension.return_value = 16
        engine._model = model
        out = engine.encode_query("hello")
        assert out.shape == (1, 16)


class TestVectorIndexMocks:
    """Drive Vector index paths with a mocked backend."""

    def _index(self, tmp_path):
        return VectorIndex(_config(tmp_path))

    def test_properties_when_backend_missing(self, tmp_path):
        idx = self._index(tmp_path)
        assert not idx.is_trained
        assert idx.count == 0
        assert idx.snippet_ids == ()

    def test_build_empty_snippets(self, tmp_path, mocker):
        search_module = pytest.importorskip("snipcontext.core.search")
        original = search_module.SEMANTIC_AVAILABLE
        try:
            search_module.SEMANTIC_AVAILABLE = True
            backend = MagicMock()
            mocker.patch("snipcontext.core.index_backends._create_backend", return_value=backend)
            idx = self._index(tmp_path)
            engine = MagicMock()
            idx.build([], engine)
            assert idx._backend is None
            assert idx.count == 0
            assert idx._id_set == set()
        finally:
            search_module.SEMANTIC_AVAILABLE = original

    def test_add_and_remove_vector(self, tmp_path, mocker):
        search_module = pytest.importorskip("snipcontext.core.search")
        pytest.importorskip("faiss")
        original = search_module.SEMANTIC_AVAILABLE
        try:
            search_module.SEMANTIC_AVAILABLE = True
            backend = MagicMock()
            backend.is_trained = True
            backend.snippet_ids = ["x"]
            backend.add.return_value = None
            backend.remove.return_value = None
            mocker.patch("snipcontext.core.index_backends._create_backend", return_value=backend)

            idx = self._index(tmp_path)
            engine = MagicMock()
            engine.encode.return_value = np.zeros((1, 16), dtype=np.float32)
            snippet = _snippet("x")
            snippet.embedding = None
            idx.build([snippet], engine)
            idx.add_vector(snippet, engine)
            assert "x" in idx._id_set
            idx.remove_vector("x")
            assert "x" not in idx._id_set
        finally:
            search_module.SEMANTIC_AVAILABLE = original

    def test_search_when_not_trained(self, tmp_path):
        idx = self._index(tmp_path)
        q = np.zeros((1, 16), dtype=np.float32)
        assert idx.search(q, top_k=3) == []

    def test_save_and_load_roundtrip(self, tmp_path, mocker):
        search_module = pytest.importorskip("snipcontext.core.search")
        pytest.importorskip("faiss")
        original = search_module.SEMANTIC_AVAILABLE
        try:
            search_module.SEMANTIC_AVAILABLE = True
            backend = MagicMock()
            backend.is_trained = True
            backend.count = 1
            backend.snippet_ids = ["x"]

            def fake_save(path):
                path.mkdir(parents=True, exist_ok=True)

            backend.save.side_effect = fake_save
            backend.load.return_value = True
            mocker.patch("snipcontext.core.index_backends._create_backend", return_value=backend)

            idx = self._index(tmp_path)
            engine = MagicMock()
            engine.encode.return_value = np.zeros((1, 16), dtype=np.float32)
            snippet = _snippet("x")
            idx.build([snippet], engine)

            index_dir = tmp_path / "index"
            idx.save(index_dir)
            loaded = idx.load(index_dir)
            assert loaded is True
            assert "x" in idx._id_set
        finally:
            search_module.SEMANTIC_AVAILABLE = original

    def test_embed_fn_when_semantic_unavailable(self, tmp_path, mocker):
        search_module = pytest.importorskip("snipcontext.core.search")
        original = search_module.SEMANTIC_AVAILABLE
        try:
            search_module.SEMANTIC_AVAILABLE = False
            idx = self._index(tmp_path)
            with pytest.raises(ImportError):
                idx._embed_fn("hello")
        finally:
            search_module.SEMANTIC_AVAILABLE = original


class TestKeywordIndexEdgeCases:
    def test_fuzzy_search_import_error_returns_empty(self, tmp_path):
        """Without rapidfuzz, fuzzy search should gracefully return []."""

        idx = KeywordIndex(_config(tmp_path))
        idx._texts = ["hello world"]
        # rapidfuzz is not installed in this environment, so ImportError is expected.
        out = idx._fuzzy_search("hello", top_k=2, min_score=0.0)
        assert out == []

    def test_load_corrupted_index(self, tmp_path):
        idx = KeywordIndex(_config(tmp_path))
        (tmp_path / "keyword_index.pkl").write_text("not-pickle")
        loaded = idx.load(tmp_path / "keyword_index")
        assert loaded is False

    def test_load_id_map_mismatch(self, tmp_path):
        import pickle

        idx = KeywordIndex(_config(tmp_path))
        idx.build([_snippet("a")])
        data = {
            "bm25": idx._bm25,
            "corpus": [["a"], ["b"], ["c"]],
            "id_map": ["a", "b"],
            "texts": idx._texts,
        }
        (tmp_path / "keyword_index.pkl").write_bytes(pickle.dumps(data))
        loaded = idx.load(tmp_path / "keyword")
        assert loaded is False

    def test_save_skips_untrained(self, tmp_path):
        idx = KeywordIndex(_config(tmp_path))
        idx.save(tmp_path / "index")
        assert not (tmp_path / "index" / "keyword_index.pkl").exists()


class TestHybridSearchBranches:
    """Unit-level HybridSearch branch coverage with mocks."""

    def test_semantic_search_fallback_when_deps_missing(self, tmp_path, mocker):
        search_module = pytest.importorskip("snipcontext.core.search")
        original = search_module.SEMANTIC_AVAILABLE
        try:
            search_module.SEMANTIC_AVAILABLE = False
            hs = HybridSearch(_config(tmp_path))
            hs._config.search.min_score = 0.0
            fake_storage = MagicMock()
            fake_storage.get.side_effect = lambda sid: _snippet(sid)
            mocker.patch("snipcontext.core.storage.StorageEngine", return_value=fake_storage)

            hs.keyword_index.build([_snippet("a")])
            results = hs._semantic_search("query", top_k=3, min_score=0.0, storage=fake_storage)
            assert all(r.matched_by == "keyword" for r in results)
        finally:
            search_module.SEMANTIC_AVAILABLE = original

    def test_hybrid_search_empty_semantic_results(self, tmp_path, mocker):
        hs = HybridSearch(_config(tmp_path))
        hs.keyword_index.build([_snippet("a")])
        fake_storage = MagicMock()
        fake_storage.get.side_effect = lambda sid: _snippet(sid)
        hs.embedder.encode_query = MagicMock(return_value=np.zeros((1, 16), dtype=np.float32))
        hs.vector_index.search = MagicMock(return_value=[])
        mocker.patch("snipcontext.core.storage.StorageEngine", return_value=fake_storage)

        results = hs.search("query", top_k=3, mode=SearchMode.HYBRID)
        assert len(results) <= 3
        assert all(r.matched_by in ("keyword", "hybrid") for r in results)

    def test_tag_search(self, tmp_path, mocker):
        hs = HybridSearch(_config(tmp_path))
        fake_storage = MagicMock()
        snippet = _snippet("a")
        snippet.tags = ["tag1", "tag2"]
        fake_storage.get.return_value = snippet
        fake_storage.find_by_tag.side_effect = lambda tag: [snippet] if tag == "tag1" else []
        mocker.patch("snipcontext.core.storage.StorageEngine", return_value=fake_storage)

        results = hs.search("tag1", top_k=3, mode=SearchMode.TAG)
        assert len(results) == 1
        assert results[0].matched_by == "tag"
        assert results[0].highlights == ["#tag1"]

    def test_apply_filters_language_and_tag(self):
        s1 = _make_snippet_plain("a", language=Language.PYTHON, tags=["p", "q"])
        s2 = _make_snippet_plain("b", language=Language.JAVASCRIPT, tags=["q"])
        r1 = SearchResult(snippet=s1, score=0.9, matched_by="keyword")
        r2 = SearchResult(snippet=s2, score=0.8, matched_by="keyword")
        out = HybridSearch._apply_filters([r1, r2], lang_set={"python"}, tag_set={"p"})
        assert [r.snippet.id for r in out] == ["a"]

    def test_recency_boost_ordering(self):
        from datetime import datetime, timedelta, timezone

        old = _make_snippet_plain("old")
        old.created_at = datetime.now(timezone.utc) - timedelta(days=120)
        fresh = _make_snippet_plain("fresh")
        fresh.created_at = datetime.now(timezone.utc)

        results = HybridSearch._apply_recency_boost(
            [
                SearchResult(snippet=old, score=0.5, matched_by="keyword"),
                SearchResult(snippet=fresh, score=0.5, matched_by="keyword"),
            ]
        )
        assert results[0].snippet.id == "fresh"
        assert results[0].score > results[1].score

    def test_explain_attaches_keys(self):
        s = _make_snippet_plain("x")
        r = SearchResult(snippet=s, score=0.5, matched_by="keyword")
        out = HybridSearch._attach_explanations([r], "keyword")
        assert out[0].explanation is not None
        assert "base_score" in out[0].explanation
        assert "matched_by" in out[0].explanation

    def test_hydrate_skips_missing_snippet(self, tmp_path, mocker):
        hs = HybridSearch(_config(tmp_path))
        fake_storage = MagicMock()
        fake_storage.get.side_effect = lambda sid: (_ for _ in ()).throw(RuntimeError("missing"))
        mocker.patch("snipcontext.core.storage.StorageEngine", return_value=fake_storage)

        out = hs._hydrate([("missing", 0.9)], "keyword", top_k=3, storage=fake_storage)
        assert out == []
