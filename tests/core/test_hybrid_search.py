"""Unit tests for hybrid search score fusion, boosting, and edge cases (Phase 2)."""

from __future__ import annotations

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
from snipcontext.core.search import HybridSearch


def _make_snippet(snippet_id: str, tags: list[str] | None = None) -> Snippet:
    return Snippet(
        content=f"content {snippet_id}",
        metadata=SnippetMetadata(
            title=f"Title {snippet_id}",
            description="",
            language=Language.PYTHON,
        ),
        id=snippet_id,
        tags=tags or [],
    )


@pytest.fixture(autouse=True)
def _force_semantic_available(mocker):
    import snipcontext.core.search as search_module

    original = search_module.SEMANTIC_AVAILABLE
    mocker.patch.object(search_module, "SEMANTIC_AVAILABLE", True)
    yield
    search_module.SEMANTIC_AVAILABLE = original


@pytest.fixture(autouse=True)
def _patch_indices_trained(mocker):
    mocker.patch.object(
        __import__("snipcontext.core.search", fromlist=["KeywordIndex"]).KeywordIndex,
        "is_trained",
        new_callable=mocker.PropertyMock,
        return_value=True,
    )
    mocker.patch.object(
        __import__("snipcontext.core.search", fromlist=["VectorIndex"]).VectorIndex,
        "is_trained",
        new_callable=mocker.PropertyMock,
        return_value=True,
    )


@pytest.fixture
def fake_storage(mocker):
    fake_storage = mocker.MagicMock()
    fake_storage.get.side_effect = lambda sid: None
    fake_storage.save = mocker.MagicMock()
    mocker.patch("snipcontext.core.storage.StorageEngine", return_value=fake_storage)
    return fake_storage


@pytest.fixture
def hybrid_search(temp_dir):
    config = Config(
        storage=StorageConfig(data_dir=temp_dir),
        search=SearchConfig(
            top_k=10,
            min_score=0.0,
            semantic_weight=0.5,
            keyword_weight=0.5,
        ),
    )
    hs = HybridSearch(config)
    hs._keyword_dirty = False
    return hs


_HELPER_DIM = 384


def _attach_mock_encode_query(hybrid_search, mocker):
    hybrid_search.embedder.encode_query = mocker.MagicMock(
        return_value=np.zeros((1, _HELPER_DIM), dtype=np.float32)
    )


class TestHybridScoreFusion:
    def test_score_fusion_formula(self, hybrid_search, fake_storage, mocker):
        s1 = _make_snippet("a", ["auth"])
        s2 = _make_snippet("b", ["auth", "jwt"])
        s3 = _make_snippet("c", ["jwt"])
        fake_storage.get.side_effect = lambda sid, *_args, **_kwargs: {
            "a": s1,
            "b": s2,
            "c": s3,
        }.get(sid)

        _attach_mock_encode_query(hybrid_search, mocker)
        hybrid_search.keyword_index.search = mocker.MagicMock(
            return_value=[("a", 0.9), ("b", 0.1), ("c", 0.4)]
        )
        hybrid_search.vector_index.search = mocker.MagicMock(
            return_value=[("a", 0.6), ("b", 0.9), ("c", 0.2)]
        )

        results = hybrid_search.search(
            query="auth jwt",
            top_k=3,
            mode=SearchMode.HYBRID,
            min_score=0.0,
        )

        assert [r.snippet.id for r in results] == ["a", "b", "c"]
        scores = {r.snippet.id: r.score for r in results}
        assert abs(scores["a"] - 0.75) < 1e-6
        assert abs(scores["b"] - 0.5) < 1e-6
        assert abs(scores["c"] - 0.3) < 1e-6

    def test_asymmetric_weights_flip_ordering(self, hybrid_search, fake_storage, mocker):
        s_sem = _make_snippet("sem", ["other"])
        s_kw = _make_snippet("kw", ["exact"])
        fake_storage.get.side_effect = lambda sid, *_args, **_kwargs: {
            "sem": s_sem,
            "kw": s_kw,
        }.get(sid)

        _attach_mock_encode_query(hybrid_search, mocker)
        hybrid_search.keyword_index.search = mocker.MagicMock(
            return_value=[("sem", 0.1), ("kw", 0.9)]
        )
        hybrid_search.vector_index.search = mocker.MagicMock(
            return_value=[("sem", 0.9), ("kw", 0.1)]
        )

        hybrid_search._config.search.semantic_weight = 0.8
        hybrid_search._config.search.keyword_weight = 0.2
        results = hybrid_search.search(
            query="exact",
            top_k=2,
            mode=SearchMode.HYBRID,
            min_score=0.0,
        )
        assert [r.snippet.id for r in results] == ["sem", "kw"]

        hybrid_search._config.search.semantic_weight = 0.2
        hybrid_search._config.search.keyword_weight = 0.8
        results = hybrid_search.search(
            query="exact",
            top_k=2,
            mode=SearchMode.HYBRID,
            min_score=0.0,
        )
        assert [r.snippet.id for r in results] == ["kw", "sem"]

    def test_keyword_boost_moves_chunk_above_vector_only_chunk(
        self, hybrid_search, fake_storage, mocker
    ):
        s_exact = _make_snippet("exact", ["auth", "jwt"])
        s_similar = _make_snippet("similar", ["other"])
        fake_storage.get.side_effect = lambda sid, *_args, **_kwargs: {
            "exact": s_exact,
            "similar": s_similar,
        }.get(sid)

        _attach_mock_encode_query(hybrid_search, mocker)
        hybrid_search.keyword_index.search = mocker.MagicMock(
            return_value=[("exact", 1.0), ("similar", 0.0)]
        )
        hybrid_search.vector_index.search = mocker.MagicMock(
            return_value=[("exact", 0.5), ("similar", 0.5)]
        )

        results = hybrid_search.search(
            query="auth jwt",
            top_k=2,
            mode=SearchMode.HYBRID,
            min_score=0.0,
        )
        assert [r.snippet.id for r in results] == ["exact", "similar"]

    def test_empty_results(self, hybrid_search, fake_storage, mocker):
        _attach_mock_encode_query(hybrid_search, mocker)
        hybrid_search.keyword_index.search = mocker.MagicMock(return_value=[])
        hybrid_search.vector_index.search = mocker.MagicMock(return_value=[])

        results = hybrid_search.search(
            query="nothing",
            top_k=3,
            mode=SearchMode.HYBRID,
            min_score=0.0,
        )
        assert results == []

    def test_all_zero_embedding_scores_is_keyword_only_ordering(
        self, hybrid_search, fake_storage, mocker
    ):
        s1 = _make_snippet("a", ["auth"])
        s2 = _make_snippet("b", ["auth", "jwt"])
        s3 = _make_snippet("c", ["jwt"])
        fake_storage.get.side_effect = lambda sid, *_args, **_kwargs: {
            "a": s1,
            "b": s2,
            "c": s3,
        }.get(sid)

        _attach_mock_encode_query(hybrid_search, mocker)
        hybrid_search.keyword_index.search = mocker.MagicMock(
            return_value=[("a", 0.9), ("b", 0.1), ("c", 0.4)]
        )
        hybrid_search.vector_index.search = mocker.MagicMock(
            return_value=[("a", 0.0), ("b", 0.0), ("c", 0.0)]
        )

        results = hybrid_search.search(
            query="auth jwt",
            top_k=3,
            mode=SearchMode.HYBRID,
            min_score=0.0,
        )
        assert [r.snippet.id for r in results] == ["a", "c", "b"]
        assert abs(results[0].score - 0.45) < 1e-6

    def test_no_keyword_hits_is_pure_semantic_ordering(self, hybrid_search, fake_storage, mocker):
        s1 = _make_snippet("a", ["other"])
        s2 = _make_snippet("b", ["other"])
        fake_storage.get.side_effect = lambda sid, *_args, **_kwargs: {
            "a": s1,
            "b": s2,
        }.get(sid)

        _attach_mock_encode_query(hybrid_search, mocker)
        hybrid_search.keyword_index.search = mocker.MagicMock(return_value=[])
        hybrid_search.vector_index.search = mocker.MagicMock(return_value=[("a", 0.9), ("b", 0.1)])

        results = hybrid_search.search(
            query="unrelated",
            top_k=2,
            mode=SearchMode.HYBRID,
            min_score=0.0,
        )
        assert [r.snippet.id for r in results] == ["a", "b"]
        for r in results:
            assert 0.0 <= r.score <= 1.0

    def test_boost_recent_prefers_newer_snippet(self, fake_storage):
        from datetime import datetime, timedelta, timezone

        old = _make_snippet("old")
        old.created_at = datetime.now(timezone.utc) - timedelta(days=30)

        fresh = _make_snippet("fresh")
        fresh.created_at = datetime.now(timezone.utc)

        fake_storage.get.side_effect = lambda sid, *_args, **_kwargs: {
            "old": old,
            "fresh": fresh,
        }.get(sid)

        ranked = HybridSearch._apply_recency_boost(
            [
                SearchResult(snippet=old, score=0.5, matched_by="hybrid", highlights=[]),
                SearchResult(snippet=fresh, score=0.5, matched_by="hybrid", highlights=[]),
            ]
        )
        assert ranked[0].snippet.id == "fresh"
        assert ranked[0].score > ranked[1].score

    def test_empty_collection(self, hybrid_search, fake_storage, mocker):
        _attach_mock_encode_query(hybrid_search, mocker)
        hybrid_search.keyword_index.search = mocker.MagicMock(return_value=[])
        hybrid_search.vector_index.search = mocker.MagicMock(return_value=[])
        results = hybrid_search.search(
            query="none",
            top_k=3,
            mode=SearchMode.HYBRID,
            min_score=1.0,
        )
        assert results == []
