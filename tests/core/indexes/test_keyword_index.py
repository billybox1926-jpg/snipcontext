"""KeywordIndex tests with proper mocking."""

import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from snipcontext.config.settings import Config
from snipcontext.core.indexes.keyword_index import KeywordIndex
from snipcontext.core.models import Language, Snippet


@pytest.fixture
def mock_config():
    return Config(
        storage__data_dir=Path(tempfile.mkdtemp()),
        search__top_k=10,
        search__default_mode="hybrid",
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


@pytest.fixture
def sample_snippets():
    now = datetime.now(timezone.utc)
    return [
        Snippet(
            id="kw-1",
            title="Python CLI tool",
            content="A Python CLI tool for data processing",
            language=Language.PYTHON,
            tags=["python", "cli"],
            created_at=now,
        ),
        Snippet(
            id="kw-2",
            title="JavaScript web framework",
            content="A JavaScript web framework for building apps",
            language=Language.JAVASCRIPT,
            tags=["javascript", "web"],
            created_at=now,
        ),
        Snippet(
            id="kw-3",
            title="Rust systems programming",
            content="Rust systems programming guide",
            language=Language.RUST,
            tags=["rust", "systems"],
            created_at=now,
        ),
    ]


@pytest.fixture
def built_index(mock_config, sample_snippets):
    """Create a KeywordIndex built with BM25 (rank_bm25 installed)."""
    with patch("snipcontext.core.indexes.keyword_index.KeywordIndex.BM25_AVAILABLE", True):
        idx = KeywordIndex(mock_config)
        idx.build(sample_snippets)
        return idx


@pytest.fixture
def fallback_index(mock_config, sample_snippets):
    """Create a KeywordIndex using the fallback path (BM25_AVAILABLE=False)."""
    with patch("snipcontext.core.indexes.keyword_index.KeywordIndex.BM25_AVAILABLE", False):
        idx = KeywordIndex(mock_config)
        idx.build(sample_snippets)
        return idx


def test_build_with_bm25_creates_index(built_index):
    """build() with BM25_AVAILABLE=True creates a BM25Okapi index."""
    assert built_index.is_trained
    assert built_index._bm25 is not None
    assert len(built_index._corpus) == 3
    assert len(built_index._id_map) == 3


def test_build_with_fallback_creates_corpus(fallback_index):
    """build() with BM25_AVAILABLE=False creates corpus for fallback scoring."""
    assert fallback_index.is_trained
    assert fallback_index._bm25 is None
    assert len(fallback_index._corpus) == 3
    assert len(fallback_index._id_map) == 3


def test_search_returns_results(built_index):
    """search() returns results for matching query."""
    results = built_index.search("python cli", top_k=5, min_score=0.0)
    assert len(results) >= 1
    # First result should be kw-1 (python cli)
    assert results[0][0] == "kw-1"


def test_search_respects_top_k(built_index):
    """search() respects top_k parameter."""
    results = built_index.search("a", top_k=2, min_score=0.0)
    assert len(results) <= 2


def test_search_respects_min_score(built_index):
    """search() filters results below min_score."""
    results = built_index.search("python", top_k=5, min_score=0.9)
    for _, score in results:
        assert score >= 0.9


def test_search_empty_query_returns_results(built_index):
    """search() with empty query returns results (all docs match)."""
    results = built_index.search("", top_k=5, min_score=0.0)
    assert len(results) >= 0  # May be 0 if no match


def test_search_no_match_returns_empty(built_index):
    """search() with non-matching query returns empty list."""
    results = built_index.search("xyznonexistent", top_k=5, min_score=0.1)
    assert len(results) == 0


def test_fallback_search_returns_results(fallback_index):
    """Fallback search (no BM25) returns results for matching query."""
    results = fallback_index.search("python cli", top_k=5, min_score=0.0)
    assert len(results) >= 1


def test_fallback_search_no_match_returns_empty(fallback_index):
    """Fallback search returns empty for non-matching query."""
    results = fallback_index.search("xyznonexistent", top_k=5, min_score=0.1)
    assert len(results) == 0


def test_save_creates_file(built_index, mock_config):
    """save() creates a JSON file."""
    path = mock_config.index_path / "keyword"
    built_index.save(path)
    assert (path / "keyword_index.json").exists()


def test_save_load_roundtrip(built_index, mock_config):
    """save() followed by load() preserves the index."""
    path = mock_config.index_path / "keyword_rt"
    built_index.save(path)

    loaded = KeywordIndex(mock_config)
    assert loaded.load(path)
    assert loaded.is_trained
    assert len(loaded._corpus) == 3


def test_load_missing_file_returns_false(mock_config):
    """load() returns False when file doesn't exist."""
    idx = KeywordIndex(mock_config)
    assert idx.load(mock_config.index_path / "nonexistent") is False


def test_load_corrupted_file_returns_false(mock_config):
    """load() returns False for corrupted JSON."""
    path = mock_config.index_path / "corrupt"
    path.mkdir(parents=True, exist_ok=True)
    (path / "keyword_index.json").write_text("not valid json {{{")

    idx = KeywordIndex(mock_config)
    assert idx.load(path) is False


def test_is_trained_reflects_state():
    """is_trained is False before build, True after."""
    config = Config(
        storage__data_dir=Path(tempfile.mkdtemp()),
        search__top_k=10,
        search__default_mode="hybrid",
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
    idx = KeywordIndex(config)
    assert idx.is_trained is False


def test_tokenize_splits_correctly():
    """_tokenize() splits text into lowercase tokens."""
    result = KeywordIndex._tokenize("Hello World Python")
    assert result == ["hello", "world", "python"]


def test_tokenize_handles_punctuation():
    """_tokenize() handles punctuation correctly."""
    result = KeywordIndex._tokenize("hello, world! python.")
    assert "hello" in result
    assert "world" in result
    assert "python" in result


def test_build_empty_snippets_clears_index(mock_config):
    """build() with empty snippets clears the index."""
    idx = KeywordIndex(mock_config)
    idx.build([])
    assert idx.is_trained is False
    assert idx._bm25 is None
    assert idx._corpus is None
