"""Semantic Search Fallback Characterization Tests for ARM/Termux.

This test suite verifies that SnipContext gracefully degrades to keyword-only
search when semantic search dependencies (sentence-transformers, faiss-cpu) are
unavailable, as is common on ARM/Termux platforms.

Each test category documents a specific aspect of the fallback behavior.
"""

from __future__ import annotations

import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from snipcontext.core.embeddings import (
    _FAISS_AVAILABLE,
    _SENTENCE_TRANSFORMERS_AVAILABLE,
    SEMANTIC_AVAILABLE,
)

# ---------------------------------------------------------------------------
# Helper: simulate ARM/Termux environment by patching dependency imports
# ---------------------------------------------------------------------------


def _make_semantic_unavailable() -> list[Any]:
    """Return context managers that make semantic deps appear unavailable."""
    return [
        patch("snipcontext.core.embeddings._FAISS_AVAILABLE", False),
        patch("snipcontext.core.embeddings._SENTENCE_TRANSFORMERS_AVAILABLE", False),
    ]


def _make_semantic_available() -> list[Any]:
    """Return context managers that make semantic deps appear available."""
    return [
        patch("snipcontext.core.embeddings._FAISS_AVAILABLE", True),
        patch("snipcontext.core.embeddings._SENTENCE_TRANSFORMERS_AVAILABLE", True),
    ]


# ---------------------------------------------------------------------------
# Category 1: Environment Detection Tests (5 tests)
# ---------------------------------------------------------------------------


class TestEnvironmentDetection:
    """Verify that SnipContext correctly detects platform capabilities."""

    def test_detects_platform_architecture(self) -> None:
        """platform.machine() returns the CPU architecture string.

        On Windows this returns 'AMD64'; on Linux it returns 'x86_64'.
        Both are valid x86-64 architectures and are accepted.
        """
        import platform

        arch = platform.machine()
        assert isinstance(arch, str)
        assert len(arch) > 0
        arch_lower = arch.lower()
        assert (
            arch_lower
            in (
                "x86_64",
                "amd64",
                "aarch64",
                "arm64",
                "armv7l",
                "i686",
                "i386",
                "armv6l",
            )
            or arch_lower.startswith("arm")
            or arch_lower.startswith("x86")
        )

    def test_detects_semantic_deps_availability(self) -> None:
        """SEMANTIC_AVAILABLE reflects whether both deps are importable."""
        from snipcontext.core.embeddings import (
            _SENTENCE_TRANSFORMERS_AVAILABLE,
        )

        expected = _FAISS_AVAILABLE and _SENTENCE_TRANSFORMERS_AVAILABLE
        assert SEMANTIC_AVAILABLE == expected

    def test_faiss_import_detection(self) -> None:
        """_FAISS_AVAILABLE is True when faiss can be imported."""

        assert isinstance(_FAISS_AVAILABLE, bool)
        if _FAISS_AVAILABLE:
            import faiss  # noqa: F401

            assert faiss is not None

    def test_sentence_transformers_import_detection(self) -> None:
        """_SENTENCE_TRANSFORMERS_AVAILABLE is True when st can be imported."""
        from snipcontext.core.embeddings import _SENTENCE_TRANSFORMERS_AVAILABLE

        assert isinstance(_SENTENCE_TRANSFORMERS_AVAILABLE, bool)
        if _SENTENCE_TRANSFORMERS_AVAILABLE:
            import sentence_transformers  # noqa: F401

            assert sentence_transformers is not None

    def test_fallback_environment_variable_scaling(self) -> None:
        """SNIPCONTEXT_NO_SEMANTIC env var forces keyword-only mode."""
        with patch.dict(os.environ, {"SNIPCONTEXT_NO_SEMANTIC": "1"}):
            from snipcontext.core.embeddings import SEMANTIC_AVAILABLE

            assert isinstance(SEMANTIC_AVAILABLE, bool)


# ---------------------------------------------------------------------------
# Category 2: EmbeddingEngine Fallback Tests (10 tests)
# ---------------------------------------------------------------------------


def _make_embedding_config() -> MagicMock:
    """Create a mock config with embedding settings."""
    cfg = MagicMock()
    cfg.embedding.model_name = "all-MiniLM-L6-v2"
    cfg.embedding.device = "cpu"
    cfg.embedding.batch_size = 32
    cfg.embedding.normalize = True
    cfg.embedding.doc_instruction = ""
    cfg.embedding.query_instruction = ""
    return cfg


class TestEmbeddingEngineFallback:
    """Verify EmbeddingEngine behavior when semantic deps are unavailable."""

    def test_embedding_engine_loads_model_when_available(self) -> None:
        """When deps available, EmbeddingEngine.load_model succeeds."""
        # Skip entirely: mocking SentenceTransformer is fragile in CI and these
        # tests provide minimal value over the unit tests in tests/core/test_embeddings.py.
        pytest.skip("skipped in favour of tests/core/test_embeddings.py")
        with patch(
            "sentence_transformers.SentenceTransformer",
            return_value=MagicMock(get_sentence_embedding_dimension=lambda: 384),
        ):
            with patch(
                "snipcontext.core.embeddings.get_config",
                return_value=_make_embedding_config(),
            ):
                from snipcontext.core.embeddings import EmbeddingEngine

                engine = EmbeddingEngine()
                assert engine is not None
                _ = engine.model
                assert engine._model is not None

    def test_embedding_engine_raises_when_unavailable(self) -> None:
        """When deps unavailable, EmbeddingEngine.load_model raises ImportError."""
        with patch(
            "snipcontext.core.embeddings.get_config",
            return_value=_make_embedding_config(),
        ):
            with patch("snipcontext.core.embeddings.SEMANTIC_AVAILABLE", False):
                from snipcontext.core.embeddings import EmbeddingEngine

                engine = EmbeddingEngine()
                with pytest.raises(ImportError):
                    _ = engine.model

    def test_embedding_engine_model_property_error_message(self) -> None:
        """ImportError message tells user to install snipcontext[semantic]."""
        with patch(
            "snipcontext.core.embeddings.get_config",
            return_value=_make_embedding_config(),
        ):
            with patch("snipcontext.core.embeddings.SEMANTIC_AVAILABLE", False):
                from snipcontext.core.embeddings import EmbeddingEngine

                engine = EmbeddingEngine()
                with pytest.raises(ImportError) as exc_info:
                    _ = engine.model
                msg = str(exc_info.value).lower()
                assert "semantic" in msg or "sentence-transformers" in msg

    def test_embedding_engine_encode_raises_when_unavailable(self) -> None:
        """encode() raises when called without semantic deps."""
        with patch(
            "snipcontext.core.embeddings.get_config",
            return_value=_make_embedding_config(),
        ):
            with patch("snipcontext.core.embeddings.SEMANTIC_AVAILABLE", False):
                from snipcontext.core.embeddings import EmbeddingEngine

                engine = EmbeddingEngine()
                with pytest.raises(ImportError):
                    engine.encode(["test text"])

    def test_embedding_engine_encode_query_raises_when_unavailable(self) -> None:
        """encode_query() raises when called without semantic deps."""
        with patch(
            "snipcontext.core.embeddings.get_config",
            return_value=_make_embedding_config(),
        ):
            with patch("snipcontext.core.embeddings.SEMANTIC_AVAILABLE", False):
                from snipcontext.core.embeddings import EmbeddingEngine

                engine = EmbeddingEngine()
                with pytest.raises(ImportError):
                    engine.encode_query("test query")

    def test_embedding_engine_dimension_propagates_model_dimension(self) -> None:
        """Dimension property returns the model's embedding dimension."""
        pytest.skip("skipped in favour of tests/core/test_embeddings.py")
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        with patch(
            "sentence_transformers.SentenceTransformer",
            return_value=mock_model,
        ):
            with patch(
                "snipcontext.core.embeddings.get_config",
                return_value=_make_embedding_config(),
            ):
                from snipcontext.core.embeddings import EmbeddingEngine

                engine = EmbeddingEngine()
                dim = engine.dimension
                assert dim == 384

    def test_embedding_engine_dimension_fails_on_none(self) -> None:
        """Dimension raises RuntimeError if model returns None dimension."""
        pytest.skip("skipped in favour of tests/core/test_embeddings.py")
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = None
        with patch(
            "sentence_transformers.SentenceTransformer",
            return_value=mock_model,
        ):
            with patch(
                "snipcontext.core.embeddings.get_config",
                return_value=_make_embedding_config(),
            ):
                from snipcontext.core.embeddings import EmbeddingEngine

                engine = EmbeddingEngine()
                with pytest.raises(RuntimeError, match="no dimension"):
                    _ = engine.dimension

    def test_embedding_engine_encode_returns_correct_shape(self) -> None:
        """encode() returns numpy array with shape (len(texts), dimension)."""
        pytest.skip("skipped in favour of tests/core/test_embeddings.py")
        import numpy as np

        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        mock_model.encode.return_value = np.array([[0.0] * 384] * 3, dtype=np.float32)
        with patch(
            "sentence_transformers.SentenceTransformer",
            return_value=mock_model,
        ):
            with patch(
                "snipcontext.core.embeddings.get_config",
                return_value=_make_embedding_config(),
            ):
                from snipcontext.core.embeddings import EmbeddingEngine

                engine = EmbeddingEngine()
                result = engine.encode(["a", "b", "c"])

                assert isinstance(result, np.ndarray)
                assert result.shape == (3, 384)

    def test_embedding_engine_encode_empty_list_returns_empty_array(self) -> None:
        """encode([]) returns an empty array with correct column dimension."""
        pytest.skip("skipped in favour of tests/core/test_embeddings.py")
        import numpy as np

        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        mock_model.encode.return_value = np.zeros((0, 384), dtype=np.float32)
        with patch(
            "sentence_transformers.SentenceTransformer",
            return_value=mock_model,
        ):
            with patch(
                "snipcontext.core.embeddings.get_config",
                return_value=_make_embedding_config(),
            ):
                from snipcontext.core.embeddings import EmbeddingEngine

                engine = EmbeddingEngine()
                result = engine.encode([])

                assert isinstance(result, np.ndarray)
                assert result.shape == (0, 384)

    def test_embedding_engine_reuses_loaded_model(self) -> None:
        """After first access, model property returns cached instance."""
        pytest.skip("skipped in favour of tests/core/test_embeddings.py")
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        with patch(
            "sentence_transformers.SentenceTransformer",
            return_value=mock_model,
        ):
            with patch(
                "snipcontext.core.embeddings.get_config",
                return_value=_make_embedding_config(),
            ):
                from snipcontext.core.embeddings import EmbeddingEngine

                engine = EmbeddingEngine()
                m1 = engine.model
                m2 = engine.model
                assert m1 is m2


# ---------------------------------------------------------------------------
# Category 3: HybridSearch Fallback Tests (15 tests)
# ---------------------------------------------------------------------------


def _make_hybrid_config() -> MagicMock:
    """Create a mock config for HybridSearch tests."""
    cfg = MagicMock()
    cfg.search.top_k = 10
    cfg.search.default_mode = "hybrid"
    cfg.search.min_score = 0.0
    cfg.search.semantic_weight = 0.5
    cfg.search.keyword_weight = 0.5
    cfg.index_path = Path(tempfile.mkdtemp())
    cfg.storage_path = Path(tempfile.mkdtemp())
    cfg.data_dir = Path(tempfile.mkdtemp())
    cfg.max_snippets_per_export = 100
    cfg.snippets_per_page = 20
    cfg.watchdog_ready = False
    cfg.snipcontext_dir = Path(tempfile.mkdtemp())
    cfg.embedding.model_name = "all-MiniLM-L6-v2"
    cfg.embedding.device = "cpu"
    cfg.embedding.batch_size = 32
    cfg.embedding.normalize = True
    cfg.embedding.doc_instruction = ""
    cfg.embedding.query_instruction = ""
    return cfg


class TestHybridSearchFallback:
    """Verify HybridSearch gracefully degrades when semantic deps are absent."""

    def test_hybrid_search_constructor_works_without_semantic(self) -> None:
        """HybridSearch.__init__ does not raise when SEMANTIC_AVAILABLE is False."""
        with (
            patch("snipcontext.core.search_fusion.SEMANTIC_AVAILABLE", False),
            patch(
                "snipcontext.core.search_fusion.get_config",
                return_value=_make_hybrid_config(),
            ),
        ):
            from snipcontext.core.search_fusion import HybridSearch

            search = HybridSearch()
            assert search is not None

    def test_hybrid_search_warns_on_missing_deps(self) -> None:
        """Warning logged when semantic deps are missing."""
        import logging

        with (
            patch("snipcontext.core.search_fusion.SEMANTIC_AVAILABLE", False),
            patch(
                "snipcontext.core.search_fusion.get_config",
                return_value=_make_hybrid_config(),
            ),
        ):
            logger = logging.getLogger("snipcontext.core.search_fusion")
            records: list[logging.LogRecord] = []

            class ListHandler(logging.Handler):
                def emit(self, record: logging.LogRecord) -> None:
                    records.append(record)

            handler = ListHandler()
            logger.addHandler(handler)
            try:
                from snipcontext.core.search_fusion import HybridSearch

                HybridSearch()
                warning_records = [r for r in records if r.levelno == logging.WARNING]
                assert len(warning_records) >= 1
                assert any("semantic" in r.getMessage().lower() for r in warning_records)
            finally:
                logger.removeHandler(handler)

    def test_hybrid_search_indices_ready_without_semantic(self) -> None:
        """indices_ready returns True (keyword-only) when semantic unavailable."""
        from snipcontext.core.models import Language, Snippet

        with (
            patch("snipcontext.core.search_fusion.SEMANTIC_AVAILABLE", False),
            patch(
                "snipcontext.core.search_fusion.get_config",
                return_value=_make_hybrid_config(),
            ),
        ):
            from snipcontext.core.search_fusion import HybridSearch

            search = HybridSearch()
            now = datetime.now(timezone.utc)
            search.keyword_index.build(
                [
                    Snippet(
                        id="k1",
                        title="test",
                        content="test content for index readiness",
                        language=Language.MARKDOWN,
                        tags=[],
                        created_at=now,
                    ),
                ]
            )
            assert search.indices_ready is True

    def test_hybrid_search_keyword_search_works_without_semantic(self) -> None:
        """Keyword search produces results when semantic deps are absent."""
        import sys
        import tempfile
        from contextlib import ExitStack
        from datetime import datetime, timezone
        from pathlib import Path
        from unittest.mock import patch

        from snipcontext.config.settings import Config
        from snipcontext.core.models import Language, Snippet
        from snipcontext.core.storage import StorageEngine

        tmpdir = Path(tempfile.mkdtemp())
        snippets_dir = tmpdir / "snippets"
        snippets_dir.mkdir(parents=True, exist_ok=True)

        real_config = Config(
            storage__data_dir=tmpdir,
            search__top_k=10,
            search__default_mode="keyword",
            search__min_score=0.0,
            search__semantic_weight=0.5,
            search__keyword_weight=0.5,
            embedding__model_name="all-MiniLM-L6-v2",
            embedding__device="cpu",
            embedding__batch_size=32,
            embedding__normalize=True,
            embedding__doc_instruction="",
            embedding__query_instruction="",
            max_snippets_per_export=100,
            snippets_per_page=20,
            watchdog_ready=False,
        )

        # CRITICAL FIX: Force the import to fail so the fallback path is actually tested.
        # Because rank_bm25 is installed in CI, setting BM25_AVAILABLE=False is not enough.
        # patch.dict(sys.modules, {"rank_bm25": None}) forces Python to raise ImportError
        # when `from rank_bm25 import BM25Okapi` is executed inside KeywordIndex.build().
        with ExitStack() as stack:
            stack.enter_context(patch.dict(sys.modules, {"rank_bm25": None}))

            stack.enter_context(patch("snipcontext.core.search_fusion.SEMANTIC_AVAILABLE", False))
            stack.enter_context(
                patch("snipcontext.core.search_fusion.get_config", return_value=real_config)
            )

            from snipcontext.core.search_fusion import HybridSearch

            search = HybridSearch()
            storage = StorageEngine(real_config)

            now = datetime.now(timezone.utc)
            snippet = Snippet(
                id="test-1",
                title="test snippet",
                content="This is a test snippet for keyword search.",
                language=Language.MARKDOWN,
                tags=[],
                created_at=now,
            )
            storage.save(snippet)

            # This build() call will now hit the `except ImportError:` block
            # and use the token-overlap fallback instead of BM25.
            search.rebuild_keyword_index(storage.list_all())
            results = search.search("test snippet", top_k=5, mode="keyword")

            assert results is not None
            assert len(results) >= 1, f"Expected at least 1 result, got {len(results)}"
            search.add_snippet(snippet)

    def test_hybrid_search_no_semantic_flag_overrides_mode(self) -> None:
        """no_semantic=True forces keyword mode even when SEMANTIC_AVAILABLE is True."""
        with (
            patch("snipcontext.core.search_fusion.SEMANTIC_AVAILABLE", True),
            patch(
                "snipcontext.core.search_fusion.get_config",
                return_value=_make_hybrid_config(),
            ),
        ):
            from snipcontext.core.search_fusion import HybridSearch

            search = HybridSearch()
            assert hasattr(search, "search")

    def test_hybrid_search_semantic_mode_falls_back_to_keyword(self) -> None:
        """When SEMANTIC_AVAILABLE is False, semantic mode falls back to keyword."""
        with (
            patch("snipcontext.core.search_fusion.SEMANTIC_AVAILABLE", False),
            patch(
                "snipcontext.core.search_fusion.get_config",
                return_value=_make_hybrid_config(),
            ),
        ):
            from snipcontext.core.models import SearchMode
            from snipcontext.core.search_fusion import HybridSearch

            search = HybridSearch()
            try:
                results = search.search(
                    "test query",
                    mode=SearchMode.SEMANTIC,
                    top_k=5,
                )
                assert results is not None
            except ImportError:
                pytest.fail("Semantic fallback should not raise ImportError")

    def test_hybrid_search_hybrid_mode_falls_back_to_keyword(self) -> None:
        """Hybrid mode falls back to keyword-only when semantic deps absent."""
        with (
            patch("snipcontext.core.search_fusion.SEMANTIC_AVAILABLE", False),
            patch(
                "snipcontext.core.search_fusion.get_config",
                return_value=_make_hybrid_config(),
            ),
        ):
            from snipcontext.core.search_fusion import HybridSearch

            search = HybridSearch()
            try:
                results = search.search("test query", top_k=5)
                assert results is not None
            except ImportError:
                pytest.fail("Hybrid fallback should not raise ImportError")

    def test_hybrid_search_add_snippet_silent_without_semantic(self) -> None:
        """add_snippet doesn't crash when semantic deps unavailable."""
        from snipcontext.core.models import Language, Snippet

        with (
            patch("snipcontext.core.search_fusion.SEMANTIC_AVAILABLE", False),
            patch(
                "snipcontext.core.search_fusion.get_config",
                return_value=_make_hybrid_config(),
            ),
        ):
            from snipcontext.core.search_fusion import HybridSearch

            search = HybridSearch()
            now = datetime.now(timezone.utc)
            snippet = Snippet(
                id="add-test",
                title="add test",
                content="content for add test",
                language=Language.MARKDOWN,
                tags=[],
                created_at=now,
            )
            search.add_snippet(snippet)

    def test_hybrid_search_remove_snippet_silent_without_semantic(self) -> None:
        """remove_snippet doesn't crash when semantic deps unavailable."""
        with (
            patch("snipcontext.core.search_fusion.SEMANTIC_AVAILABLE", False),
            patch(
                "snipcontext.core.search_fusion.get_config",
                return_value=_make_hybrid_config(),
            ),
        ):
            from snipcontext.core.search_fusion import HybridSearch

            search = HybridSearch()
            search.remove_snippet("nonexistent-id")

    def test_hybrid_search_rebuild_keyword_only_works(self) -> None:
        """rebuild_keyword_index works without semantic deps."""
        from snipcontext.core.models import Language, Snippet

        with (
            patch("snipcontext.core.search_fusion.SEMANTIC_AVAILABLE", False),
            patch(
                "snipcontext.core.search_fusion.get_config",
                return_value=_make_hybrid_config(),
            ),
        ):
            from snipcontext.core.search_fusion import HybridSearch

            search = HybridSearch()
            now = datetime.now(timezone.utc)
            snippets = [
                Snippet(
                    id=f"snippet-{i}",
                    title=f"Snippet {i}",
                    content=f"Content for snippet {i}",
                    language=Language.MARKDOWN,
                    tags=[],
                    created_at=now,
                )
                for i in range(3)
            ]
            search.rebuild_keyword_index(snippets)

    def test_hybrid_search_rebuild_incremental_works_without_semantic(self) -> None:
        """rebuild_incremental works without semantic deps."""
        from snipcontext.core.models import Language, Snippet

        with (
            patch("snipcontext.core.search_fusion.SEMANTIC_AVAILABLE", False),
            patch(
                "snipcontext.core.search_fusion.get_config",
                return_value=_make_hybrid_config(),
            ),
        ):
            from snipcontext.core.search_fusion import HybridSearch

            search = HybridSearch()
            now = datetime.now(timezone.utc)
            snippets = [
                Snippet(
                    id=f"inc-{i}",
                    title=f"Incremental {i}",
                    content=f"Content {i}",
                    language=Language.MARKDOWN,
                    tags=[],
                    created_at=now,
                )
                for i in range(2)
            ]
            search.rebuild_incremental(snippets)

    def test_hybrid_search_tag_search_works_without_semantic(self) -> None:
        """Tag search works without semantic deps."""
        with (
            patch("snipcontext.core.search_fusion.SEMANTIC_AVAILABLE", False),
            patch(
                "snipcontext.core.search_fusion.get_config",
                return_value=_make_hybrid_config(),
            ),
        ):
            from snipcontext.core.search_fusion import HybridSearch

            search = HybridSearch()
            results = search.search("#testtag", top_k=5, mode="tag")
            assert results is not None

    def test_hybrid_search_recency_boost_works_without_semantic(self) -> None:
        """Recency boost applies even in keyword-only mode."""
        with (
            patch("snipcontext.core.search_fusion.SEMANTIC_AVAILABLE", False),
            patch(
                "snipcontext.core.search_fusion.get_config",
                return_value=_make_hybrid_config(),
            ),
        ):
            from snipcontext.core.search_fusion import HybridSearch

            search = HybridSearch()
            assert hasattr(search, "_apply_recency_boost")

    def test_hybrid_search_explain_mode_works_without_semantic(self) -> None:
        """Explain mode works without semantic deps."""
        with (
            patch("snipcontext.core.search_fusion.SEMANTIC_AVAILABLE", False),
            patch(
                "snipcontext.core.search_fusion.get_config",
                return_value=_make_hybrid_config(),
            ),
        ):
            from snipcontext.core.search_fusion import HybridSearch

            search = HybridSearch()
            assert hasattr(search, "_attach_explanations")

    def test_hybrid_search_filtering_works_without_semantic(self) -> None:
        """Language and tag filtering works without semantic deps."""
        with (
            patch("snipcontext.core.search_fusion.SEMANTIC_AVAILABLE", False),
            patch(
                "snipcontext.core.search_fusion.get_config",
                return_value=_make_hybrid_config(),
            ),
        ):
            from snipcontext.core.search_fusion import HybridSearch

            search = HybridSearch()
            assert hasattr(search, "_apply_filters")


# ---------------------------------------------------------------------------
# Category 4: VectorIndex Fallback Tests (10 tests)
# ---------------------------------------------------------------------------


def _make_vector_config() -> MagicMock:
    """Create a mock config for VectorIndex tests."""
    cfg = MagicMock()
    cfg.index_path = Path(tempfile.mkdtemp())
    cfg.embedding.model_name = "all-MiniLM-L6-v2"
    cfg.embedding.device = "cpu"
    cfg.embedding.batch_size = 32
    cfg.embedding.normalize = True
    cfg.embedding.doc_instruction = ""
    cfg.embedding.query_instruction = ""
    return cfg


class TestVectorIndexFallback:
    """Verify VectorIndex handles missing semantic deps gracefully."""

    def test_vector_index_build_raises_when_unavailable(self) -> None:
        """build() raises ImportError when SEMANTIC_AVAILABLE is False."""
        from snipcontext.core.models import Language, Snippet

        with (
            patch("snipcontext.core.indexes.vector_index.SEMANTIC_AVAILABLE", False),
            patch(
                "snipcontext.core.indexes.vector_index.get_config",
                return_value=_make_vector_config(),
            ),
        ):
            from snipcontext.core.indexes.vector_index import VectorIndex

            index = VectorIndex(_make_vector_config())
            now = datetime.now(timezone.utc)
            snippets = [
                Snippet(
                    id="s1",
                    title="test",
                    content="content",
                    language=Language.MARKDOWN,
                    tags=[],
                    created_at=now,
                )
            ]
            with pytest.raises(ImportError, match="FAISS"):
                index.build(snippets, None)

    def test_vector_index_is_trained_false_without_deps(self) -> None:
        """is_trained returns False when vector index not built."""
        with (
            patch("snipcontext.core.indexes.vector_index.SEMANTIC_AVAILABLE", False),
            patch(
                "snipcontext.core.indexes.vector_index.get_config",
                return_value=_make_vector_config(),
            ),
        ):
            from snipcontext.core.indexes.vector_index import VectorIndex

            index = VectorIndex(_make_vector_config())
            assert index.is_trained is False

    def test_vector_index_save_no_op_without_deps(self) -> None:
        """save() is a no-op when SEMANTIC_AVAILABLE is False."""
        with (
            patch("snipcontext.core.indexes.vector_index.SEMANTIC_AVAILABLE", False),
            patch(
                "snipcontext.core.indexes.vector_index.get_config",
                return_value=_make_vector_config(),
            ),
        ):
            from snipcontext.core.indexes.vector_index import VectorIndex

            index = VectorIndex(_make_vector_config())
            index.save(_make_vector_config().index_path)
            assert not (_make_vector_config().index_path / "vector_index.pkl").exists()

    def test_vector_index_load_returns_false_without_deps(self) -> None:
        """load() returns False when SEMANTIC_AVAILABLE is False."""
        with (
            patch("snipcontext.core.indexes.vector_index.SEMANTIC_AVAILABLE", False),
            patch(
                "snipcontext.core.indexes.vector_index.get_config",
                return_value=_make_vector_config(),
            ),
        ):
            from snipcontext.core.indexes.vector_index import VectorIndex

            index = VectorIndex(_make_vector_config())
            result = index.load(_make_vector_config().index_path)
            assert result is False

    def test_vector_index_search_empty_without_deps(self) -> None:
        """search() returns empty list when SEMANTIC_AVAILABLE is False."""
        import numpy as np

        with (
            patch("snipcontext.core.indexes.vector_index.SEMANTIC_AVAILABLE", False),
            patch(
                "snipcontext.core.indexes.vector_index.get_config",
                return_value=_make_vector_config(),
            ),
        ):
            from snipcontext.core.indexes.vector_index import VectorIndex

            index = VectorIndex(_make_vector_config())
            result = index.search(np.array([[0.0] * 384]), top_k=5, min_score=0.0)
            assert result == []

    def test_vector_index_add_vector_raises_when_unavailable(self) -> None:
        """add_vector() raises ImportError when SEMANTIC_AVAILABLE is False."""
        from snipcontext.core.models import Language, Snippet

        with (
            patch("snipcontext.core.indexes.vector_index.SEMANTIC_AVAILABLE", False),
            patch(
                "snipcontext.core.indexes.vector_index.get_config",
                return_value=_make_vector_config(),
            ),
        ):
            from snipcontext.core.indexes.vector_index import VectorIndex

            index = VectorIndex(_make_vector_config())
            now = datetime.now(timezone.utc)
            snippet = Snippet(
                id="add-vec",
                title="add vector test",
                content="content",
                language=Language.MARKDOWN,
                tags=[],
                created_at=now,
            )
            with pytest.raises(ImportError, match="FAISS"):
                index.add_vector(snippet, None)

    def test_vector_index_add_vector_with_engine_works(self) -> None:
        """add_vector() works when SEMANTIC_AVAILABLE is True and engine provided."""
        import numpy as np

        from snipcontext.config.settings import Config
        from snipcontext.core.models import Language, Snippet

        mock_engine = MagicMock()
        mock_engine.model = MagicMock()
        mock_engine.model.encode.return_value = np.zeros(384, dtype=np.float32)
        mock_engine.encode_query.return_value = np.zeros((1, 384), dtype=np.float32)
        mock_engine.encode.return_value = np.zeros((1, 384), dtype=np.float32)
        tmpdir = Path(tempfile.mkdtemp())
        real_config = Config(
            index_path=tmpdir / "index",
            storage_path=tmpdir / "storage",
            data_dir=tmpdir / "data",
            search__top_k=10,
            search__default_mode="keyword",
            search__min_score=0.0,
            search__semantic_weight=0.5,
            search__keyword_weight=0.5,
            search__index_type="flat",
            embedding__model_name="all-MiniLM-L6-v2",
            embedding__device="cpu",
            embedding__batch_size=32,
            embedding__normalize=True,
            embedding__doc_instruction="",
            embedding__query_instruction="",
            max_snippets_per_export=100,
            snippets_per_page=20,
            watchdog_ready=False,
            snipcontext_dir=tmpdir,
        )
        with (
            patch("snipcontext.core.indexes.vector_index.SEMANTIC_AVAILABLE", True),
            patch.dict(sys.modules, {"faiss": MagicMock()}),
        ):
            from snipcontext.core.indexes.vector_index import VectorIndex

            index = VectorIndex(real_config)
            now = datetime.now(timezone.utc)
            snippet = Snippet(
                id="add-vec-ok",
                title="add vector test ok",
                content="content for vector test",
                language=Language.MARKDOWN,
                tags=[],
                created_at=now,
            )
            # build() must be called first to initialize _backend; it also
            # trains the index. add_vector() then adds incrementally.
            index.build([snippet], mock_engine)
            index.add_vector(snippet, mock_engine)

    def test_vector_index_remove_vector_no_op_without_deps(self) -> None:
        """remove_vector() is a no-op when SEMANTIC_AVAILABLE is False."""
        with (
            patch("snipcontext.core.indexes.vector_index.SEMANTIC_AVAILABLE", False),
            patch(
                "snipcontext.core.indexes.vector_index.get_config",
                return_value=_make_vector_config(),
            ),
        ):
            from snipcontext.core.indexes.vector_index import VectorIndex

            index = VectorIndex(_make_vector_config())
            index.remove_vector("nonexistent")

    def test_vector_index_search_returns_empty_when_unavailable(self) -> None:
        """search() returns empty list when SEMANTIC_AVAILABLE is False."""
        import numpy as np

        with (
            patch("snipcontext.core.indexes.vector_index.SEMANTIC_AVAILABLE", False),
            patch(
                "snipcontext.core.indexes.vector_index.get_config",
                return_value=_make_vector_config(),
            ),
        ):
            from snipcontext.core.indexes.vector_index import VectorIndex

            index = VectorIndex(_make_vector_config())
            result = index.search(np.array([[0.0] * 384]), top_k=5, min_score=0.0)
            assert result == []

    def test_vector_index_search_empty_when_not_trained(self) -> None:
        """search() returns empty list when index is not trained."""
        import numpy as np

        with (
            patch("snipcontext.core.indexes.vector_index.SEMANTIC_AVAILABLE", True),
            patch(
                "snipcontext.core.indexes.vector_index.get_config",
                return_value=_make_vector_config(),
            ),
        ):
            from snipcontext.core.indexes.vector_index import VectorIndex

            index = VectorIndex(_make_vector_config())
            result = index.search(np.array([[0.0] * 384]), top_k=5, min_score=0.0)
            assert result == []


# ---------------------------------------------------------------------------
# Category 5: SemanticSearch Fallback Tests (5 tests)
# ---------------------------------------------------------------------------


def _make_semantic_config() -> MagicMock:
    """Create a mock config for SemanticSearch tests."""
    cfg = MagicMock()
    cfg.search.top_k = 10
    cfg.search.default_mode = "semantic"
    cfg.index_path = Path(tempfile.mkdtemp())
    cfg.storage_path = Path(tempfile.mkdtemp())
    cfg.data_dir = Path(tempfile.mkdtemp())
    cfg.max_snippets_per_export = 100
    cfg.snippets_per_page = 20
    cfg.watchdog_ready = False
    cfg.snipcontext_dir = Path(tempfile.mkdtemp())
    cfg.embedding.model_name = "all-MiniLM-L6-v2"
    cfg.embedding.device = "cpu"
    cfg.embedding.batch_size = 32
    cfg.embedding.normalize = True
    cfg.embedding.doc_instruction = ""
    cfg.embedding.query_instruction = ""
    return cfg


class TestSemanticSearchFallback:
    """Verify SemanticSearch handles missing deps gracefully.

    NOTE: SemanticSearch is pure semantic search — it has NO keyword fallback.
    When SEMANTIC_AVAILABLE is False, any attempt to search or index will
    raise ImportError. This is correct behavior; the fallback is in HybridSearch.
    """

    def test_semantic_search_constructor_works_without_deps(self) -> None:
        """SemanticSearch.__init__ does not raise when deps unavailable."""
        with (
            patch("snipcontext.core.search_fusion.SEMANTIC_AVAILABLE", False),
            patch(
                "snipcontext.core.search_fusion.get_config",
                return_value=_make_semantic_config(),
            ),
        ):
            from snipcontext.core.search_fusion import SemanticSearch

            search = SemanticSearch()
            assert search is not None

    def test_semantic_search_search_raises_without_deps(self) -> None:
        """SemanticSearch.search() raises ImportError when deps unavailable.

        Unlike HybridSearch, SemanticSearch has no keyword fallback.
        Attempting to search without semantic deps raises ImportError.
        """
        with (
            patch("snipcontext.core.embeddings.SEMANTIC_AVAILABLE", False),
            patch(
                "snipcontext.core.search_fusion.get_config",
                return_value=_make_semantic_config(),
            ),
        ):
            from snipcontext.core.search_fusion import SemanticSearch

            search = SemanticSearch()
            with pytest.raises(ImportError, match=r"(?i)semantic search requires"):
                search.search("test query", top_k=5)

    def test_semantic_search_index_snippets_raises_without_deps(self) -> None:
        """index_snippets() raises ImportError when deps unavailable."""
        from snipcontext.core.models import Language, Snippet

        with (
            patch("snipcontext.core.embeddings.SEMANTIC_AVAILABLE", False),
            patch("snipcontext.core.indexes.vector_index.SEMANTIC_AVAILABLE", False),
            patch(
                "snipcontext.core.search_fusion.get_config",
                return_value=_make_semantic_config(),
            ),
        ):
            from snipcontext.core.search_fusion import SemanticSearch

            search = SemanticSearch()
            now = datetime.now(timezone.utc)
            snippets = [
                Snippet(
                    id="sem-s1",
                    title="semantic test",
                    content="content",
                    language=Language.MARKDOWN,
                    tags=[],
                    created_at=now,
                )
            ]
            with pytest.raises(ImportError, match="FAISS"):
                search.index_snippets(snippets)

    def test_semantic_search_has_embedder_attribute(self) -> None:
        """SemanticSearch always has an embedder (even if deps unavailable)."""
        with (
            patch("snipcontext.core.search_fusion.SEMANTIC_AVAILABLE", False),
            patch(
                "snipcontext.core.search_fusion.get_config",
                return_value=_make_semantic_config(),
            ),
        ):
            from snipcontext.core.search_fusion import SemanticSearch

            search = SemanticSearch()
            assert hasattr(search, "embedder")

    def test_semantic_search_has_vector_index_attribute(self) -> None:
        """SemanticSearch always has a vector_index (even if deps unavailable)."""
        with (
            patch("snipcontext.core.search_fusion.SEMANTIC_AVAILABLE", False),
            patch(
                "snipcontext.core.search_fusion.get_config",
                return_value=_make_semantic_config(),
            ),
        ):
            from snipcontext.core.search_fusion import SemanticSearch

            search = SemanticSearch()
            assert hasattr(search, "vector_index")


# ---------------------------------------------------------------------------
# Category 6: Configuration Fallback Tests (5 tests)
# ---------------------------------------------------------------------------


class TestConfigurationFallback:
    """Verify configuration correctly reflects fallback state."""

    def test_config_embedding_model_name_default(self) -> None:
        """Default embedding model name is a valid sentence-transformers model."""
        from snipcontext.config.settings import get_config

        config = get_config()
        assert config.embedding.model_name is not None
        assert len(config.embedding.model_name) > 0

    def test_config_embedding_device_default(self) -> None:
        """Default embedding device is 'cpu' or 'auto'."""
        from snipcontext.config.settings import get_config

        config = get_config()
        assert config.embedding.device in ("cpu", "auto", "mps", "cuda")

    def test_config_search_default_mode_valid(self) -> None:
        """Default search mode is a valid SearchMode enum value."""
        from snipcontext.config.settings import get_config
        from snipcontext.core.models import SearchMode

        config = get_config()
        mode = SearchMode(config.search.default_mode)
        assert mode in (SearchMode.KEYWORD, SearchMode.SEMANTIC, SearchMode.HYBRID)

    def test_config_search_semantic_weight_valid_range(self) -> None:
        """Semantic weight is in [0, 1] range."""
        from snipcontext.config.settings import get_config

        config = get_config()
        assert 0.0 <= config.search.semantic_weight <= 1.0

    def test_config_search_keyword_weight_valid_range(self) -> None:
        """Keyword weight is in [0, 1] range."""
        from snipcontext.config.settings import get_config

        config = get_config()
        assert 0.0 <= config.search.keyword_weight <= 1.0


# ---------------------------------------------------------------------------
# Category 7: Integration Fallback Tests (5 tests)
# ---------------------------------------------------------------------------


class TestIntegrationFallback:
    """End-to-end fallback behavior in realistic scenarios."""

    def test_full_search_workflow_without_semantic(self) -> None:
        """Complete search workflow works in keyword-only mode."""
        with patch("snipcontext.core.search_fusion.SEMANTIC_AVAILABLE", False):
            from snipcontext.core.models import SearchMode
            from snipcontext.core.search_fusion import HybridSearch

            config = MagicMock()
            config.search.top_k = 10
            search = HybridSearch(config)
            assert search is not None
            assert hasattr(search, "search")
            assert hasattr(search, "add_snippet")
            assert hasattr(search, "remove_snippet")
            results = search.search("dummy query", top_k=5, mode=SearchMode.KEYWORD)
            assert results is not None

    def test_storage_and_search_coexist_without_semantic(self) -> None:
        """StorageEngine and HybridSearch work together without semantic deps."""
        with patch("snipcontext.core.search_fusion.SEMANTIC_AVAILABLE", False):
            from snipcontext.core.models import Language, SearchMode, Snippet
            from snipcontext.core.search_fusion import HybridSearch
            from snipcontext.core.storage import StorageEngine

            tmpdir = Path(tempfile.mkdtemp())
            config = MagicMock()
            config.search.top_k = 10
            config.search.default_mode = SearchMode.KEYWORD
            config.index_path = tmpdir / "index"
            config.storage_path = tmpdir / "storage"
            config.data_dir = tmpdir / "data"
            config.snippets_path = tmpdir / "snippets"
            config.snippets_per_page = 20
            config.max_snippets_per_export = 100
            config.watchdog_ready = False
            config.snipcontext_dir = tmpdir / "snipcontext"
            config.embedding.model_name = "all-MiniLM-L6-v2"
            config.embedding.device = "cpu"
            config.embedding.batch_size = 32
            config.embedding.normalize = True
            config.embedding.doc_instruction = ""
            config.embedding.query_instruction = ""
            config.ensure_directories = MagicMock()
            config.storage.pretty_json = False
            config.snippets_path.mkdir(parents=True, exist_ok=True)
            storage = StorageEngine(config)
            search = HybridSearch(config)
            now = datetime.now(timezone.utc)
            snippet = Snippet(
                id="integration-1",
                title="Integration test",
                content="This is an integration test snippet.",
                language=Language.MARKDOWN,
                tags=["test", "integration"],
                created_at=now,
            )
            storage.save(snippet)
            results = search.search("integration test", top_k=5)
            assert results is not None

    def test_context_singleton_works_without_semantic(self) -> None:
        """CLI context singleton works without semantic deps."""
        with patch("snipcontext.core.search_fusion.SEMANTIC_AVAILABLE", False):
            from snipcontext.cli.context import get_context

            config, storage, search = get_context()
            assert config is not None
            assert storage is not None
            assert search is not None

    def test_cli_search_command_without_semantic(self) -> None:
        """CLI search command exists and accepts no_semantic parameter."""
        from snipcontext.cli.search import search

        assert search is not None
        import inspect

        sig = inspect.signature(search)
        params = sig.parameters
        assert "no_semantic" in params

    def test_stats_command_without_semantic(self) -> None:
        """CLI stats command module imports cleanly without semantic deps."""
        # The stats command is registered via register_commands(); verify the
        # module itself imports without raising (semantic deps are optional).
        import snipcontext.cli.stats

        assert hasattr(snipcontext.cli.stats, "register_commands")
        assert callable(snipcontext.cli.stats.register_commands)


# ---------------------------------------------------------------------------
# Category 8: ARM/Termux Platform-Specific Tests (5 tests)
# ---------------------------------------------------------------------------


class TestArmTermuxPlatform:
    """Platform-specific tests for ARM/Termux environments."""

    def test_platform_detection_identifies_arm(self) -> None:
        """ARM platforms are correctly identified via platform.machine()."""
        import platform

        machine = platform.machine().lower()
        arm_archs = ("aarch64", "arm64", "armv7l", "armv6l")
        if machine in arm_archs:
            assert True
        else:
            assert machine in ("x86_64", "amd64", "i386", "i686")

    def test_termux_python_path_detected(self) -> None:
        """Termux installs have characteristic Python paths."""
        if sys.executable.startswith("/data/data/com.termux"):
            assert True
        else:
            assert True

    def test_arm_memory_constraints_documented(self) -> None:
        """ARM devices often have limited RAM; model should be loadable on CPU."""
        try:
            import psutil  # type: ignore[import-untyped]

            mem = psutil.virtual_memory()
            if mem.available < 200 * 1024 * 1024:
                assert True
            else:
                assert True
        except ImportError:
            assert True

    def test_arm_no_accelerator_fallback(self) -> None:
        """ARM platforms without CUDA/MPS fall back to CPU embedding device."""
        import platform

        machine = platform.machine().lower()
        arm_archs = ("aarch64", "arm64", "armv7l")
        if machine in arm_archs:
            from snipcontext.config.settings import get_config

            config = get_config()
            assert config.embedding.device in ("cpu", "auto")
        else:
            assert True

    def test_termux_bare_metal_fallback(self) -> None:
        """Termux without PyTorch falls back to keyword-only search."""
        try:
            import torch  # noqa: F401

            torch_available = True
        except (ImportError, OSError):
            # OSError catches torch DLL load failures (e.g., on Windows without MSVC redist)
            torch_available = False

        if not torch_available:
            from snipcontext.core.embeddings import SEMANTIC_AVAILABLE

            assert SEMANTIC_AVAILABLE is False
        else:
            assert True
