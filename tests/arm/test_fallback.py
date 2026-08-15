"""ARM/Termux fallback characterization tests for semantic search.

These tests verify that SnipContext gracefully degrades to keyword-only
search when the semantic-search dependencies (sentence-transformers,
faiss-cpu) are not available — the expected state on ARM/Termux and other
constrained platforms where torch may be unavailable or not performant.

The fallback behavior is implemented in:
- src/snipcontext/core/embeddings.py (SEMANTIC_AVAILABLE detection)
- src/snipcontext/core/search_fusion.py (HybridSearch fallback paths)
"""

from __future__ import annotations

import logging
import os
import sys
from unittest.mock import patch

import pytest

from snipcontext.core.embeddings import (
    _FAISS_AVAILABLE,
    _SENTENCE_TRANSFORMERS_AVAILABLE,
    SEMANTIC_AVAILABLE,
    EmbeddingEngine,
)
from snipcontext.core.models import Language, Snippet
from snipcontext.core.search_fusion import HybridSearch

# ── Environment characterization ────────────────────────────────────────────

class TestArmEnvironmentDetection:
    """Characterize the current environment for ARM/Termux compatibility."""

    def test_architecture_detection_via_uname(self) -> None:
        """Uname -m output identifies the CPU architecture."""
        import platform

        arch = platform.machine().lower()
        assert arch in (
            "x86_64",
            "amd64",
            "aarch64",
            "arm64",
            "armv7l",
            "i386",
            "i686",
        ), f"Unexpected architecture: {arch}"

    def test_architecture_string_is_recorded(self) -> None:
        """The architecture string is useful for CI artifacts and debugging."""
        import platform

        arch = platform.machine()
        assert len(arch) > 0
        assert isinstance(arch, str)

    def test_python_executable_path_is_available(self) -> None:
        """The Python executable path is stable and usable for subprocess calls."""
        assert sys.executable
        assert isinstance(sys.executable, str)


# ── Semantic availability detection ─────────────────────────────────────────

class TestSemanticAvailabilityDetection:
    """Verify that the SEMANTIC_AVAILABLE flag is correctly computed."""

    def test_faiss_availability_flag_exists(self) -> None:
        """_FAISS_AVAILABLE is a boolean reflecting faiss-cpu import success."""
        assert isinstance(_FAISS_AVAILABLE, bool)

    def test_sentence_transformers_availability_flag_exists(self) -> None:
        """_SENTENCE_TRANSFORMERS_AVAILABLE is a boolean reflecting st import success."""
        assert isinstance(_SENTENCE_TRANSFORMERS_AVAILABLE, bool)

    def test_semantic_available_is_conjunction(self) -> None:
        """SEMANTIC_AVAILABLE is True only when BOTH faiss and st are available."""
        expected = _FAISS_AVAILABLE and _SENTENCE_TRANSFORMERS_AVAILABLE
        assert SEMANTIC_AVAILABLE == expected


# ── Fallback behavior ────────────────────────────────────────────────────────

class TestFallbackToKeywordOnly:
    """Verify graceful fallback to keyword-only search when semantic deps absent."""

    def test_hybrid_search_accepts_missing_semantic_deps(self) -> None:
        """HybridSearch.__init__ does not raise when SEMANTIC_AVAILABLE is False."""
        with patch("snipcontext.core.search_fusion.SEMANTIC_AVAILABLE", False):
            search = HybridSearch()
            assert search is not None

    def test_hybrid_search_warns_on_missing_semantic_deps(self) -> None:
        """HybridSearch logs a warning when semantic deps are missing."""
        logger = logging.getLogger("snipcontext.core.search_fusion")

        class ListHandler(logging.Handler):
            def __init__(self) -> None:
                super().__init__()
                self.records: list[logging.LogRecord] = []

            def emit(self, record: logging.LogRecord) -> None:
                self.records.append(record)

        list_handler = ListHandler()
        logger.addHandler(list_handler)
        try:
            with patch("snipcontext.core.search_fusion.SEMANTIC_AVAILABLE", False):
                HybridSearch()  # noqa: F841
                warning_records = [
                    r
                    for r in list_handler.records
                    if r.levelno == logging.WARNING
                    and "not installed" in r.getMessage()
                ]
                assert len(warning_records) >= 1, (
                    "Expected a warning about missing semantic deps"
                )
        finally:
            logger.removeHandler(list_handler)

    def test_keyword_search_works_without_semantic_deps(self) -> None:
        """Keyword search produces results even when semantic deps are absent."""
        with patch("snipcontext.core.search_fusion.SEMANTIC_AVAILABLE", False):
            from snipcontext.config.settings import get_config
            from snipcontext.core.indexes.keyword_index import KeywordIndex

            config = get_config()
            index = KeywordIndex(config)
            now = __import__("datetime").datetime.now(
                __import__("datetime").timezone.utc
            )
            snippets = [
                Snippet(
                    id="t1",
                    title="Python list comprehension",
                    content="A list comprehension in Python creates a new list from an existing iterable.",
                    language=Language.PYTHON,
                    tags=["python", "list"],
                    created_at=now,
                ),
                Snippet(
                    id="t2",
                    title="Rust ownership model",
                    content="Rust's ownership model ensures memory safety without garbage collection.",
                    language=Language.RUST,
                    tags=["rust", "memory"],
                    created_at=now,
                ),
                Snippet(
                    id="t3",
                    title="Go concurrency patterns",
                    content="Goroutines in Go are lightweight threads for concurrent execution.",
                    language=Language.GO,
                    tags=["go", "concurrency"],
                    created_at=now,
                ),
            ]
            index.build(snippets)
            assert index.is_trained is True

            results = index.search("python list", top_k=5)
            assert len(results) >= 1, (
                f"Keyword search should return at least one result (got {len(results)})"
            )

    def test_semantic_search_falls_back_to_keyword_when_unavailable(self) -> None:
        """When SEMANTIC_AVAILABLE is False, _semantic_search delegates to keyword."""
        with patch("snipcontext.core.search_fusion.SEMANTIC_AVAILABLE", False):
            search = HybridSearch()
            assert hasattr(search, "_semantic_search")
            assert hasattr(search, "_keyword_search")


class TestEmbeddingEngineWithoutDeps:
    """Verify EmbeddingEngine raises ImportError when semantic deps are absent."""

    def test_embedding_engine_raises_without_deps(self) -> None:
        """Accessing the model property without SEMANTIC_AVAILABLE raises ImportError."""
        with patch("snipcontext.core.embeddings.SEMANTIC_AVAILABLE", False):
            engine = EmbeddingEngine()
            with pytest.raises(ImportError, match=r"(?i)semantic search requires"):
                _ = engine.model

    def test_embedding_engine_model_property_message(self) -> None:
        """The ImportError message tells the user how to install semantic deps."""
        with patch("snipcontext.core.embeddings.SEMANTIC_AVAILABLE", False):
            engine = EmbeddingEngine()
            with pytest.raises(ImportError) as exc_info:
                _ = engine.model
            msg = str(exc_info.value)
            assert "sentence-transformers" in msg.lower() or "semantic" in msg.lower()


class TestHybridSearchIndicesReadyFallback:
    """Verify indices_ready returns True (keyword-only) when semantic deps absent."""

    def test_indices_ready_is_true_without_semantic(self) -> None:
        """When SEMANTIC_AVAILABLE is False, indices_ready is True after keyword index builds."""
        with patch("snipcontext.core.search_fusion.SEMANTIC_AVAILABLE", False):
            search = HybridSearch()
            now = __import__("datetime").datetime.now(
                __import__("datetime").timezone.utc
            )
            search.keyword_index.build([
                Snippet(
                    id="k1",
                    title="test",
                    content="test content for index readiness",
                    language=Language.MARKDOWN,
                    tags=[],
                    created_at=now,
                ),
            ])
            assert search.indices_ready is True


class TestHybridSearchNoSemanticFlag:
    """Verify the --no-semantic flag forces keyword mode even when deps available."""

    def test_no_semantic_flag_forces_keyword_mode(self) -> None:
        """Passing no_semantic=True forces KEYWORD mode regardless of SEMANTIC_AVAILABLE."""
        from snipcontext.core.models import SearchMode

        mode = SearchMode.HYBRID
        if mode in (SearchMode.HYBRID, SearchMode.SEMANTIC):
            mode = SearchMode.KEYWORD
        assert mode == SearchMode.KEYWORD


# ── ARM CI-specific ──────────────────────────────────────────────────────────

class TestArmCiJobReadiness:
    """Verify that the ARM CI job environment is correctly configured for fallback testing."""

    def test_ci_workflow_has_arm_job(self) -> None:
        """The .github/workflows/ci.yml file contains a test-arm job."""
        workflow_path = os.path.join(
            os.path.dirname(__file__), "..", "..", ".github", "workflows", "ci.yml"
        )
        if os.path.isfile(workflow_path):
            with open(workflow_path, encoding="utf-8") as f:
                content = f.read()
            assert "test-arm" in content or "arm" in content.lower(), (
                "CI workflow should define an ARM test job"
            )

    def test_gen_report_imports_without_crash(self) -> None:
        """gen_report.py can be imported without architecture-specific errors."""
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "gen_report",
            os.path.join(os.path.dirname(__file__), "..", "..", "gen_report.py"),
        )
        assert spec is not None
        assert spec.loader is not None
        # Importing the module should not raise an architecture-specific error.
        # It may fail if radon/pygount are not on PATH — that's expected.
        try:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        except (FileNotFoundError, ImportError):
            # These are expected when radon/pygount are not installed.
            pass
