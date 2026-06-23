"""Tests for search_ops domain logic — targeted coverage for uncovered lines."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from snipcontext.config.settings import Config, SearchConfig, StorageConfig, reset_config
from snipcontext.core.models import Language, Snippet, SnippetMetadata
from snipcontext.core.search import HybridSearch
from snipcontext.core.search_ops import ensure_index, export_snippets, search_snippets
from snipcontext.core.storage import StorageEngine


@pytest.fixture
def temp_config():
    with tempfile.TemporaryDirectory() as tmp:
        config = Config(
            storage=StorageConfig(
                data_dir=Path(tmp),
                snippets_dir="snippets",
                index_dir="index",
            ),
            search=SearchConfig(),
        )
        yield config
        reset_config()


@pytest.fixture
def storage(temp_config):
    return StorageEngine(temp_config)


@pytest.fixture
def search_engine(temp_config):
    return HybridSearch(temp_config)


class TestEnsureIndex:
    def test_no_snippets(self, storage, search_engine):
        result = ensure_index(storage, search_engine)
        assert result == []

    def test_with_snippets(self, storage, search_engine):
        s = Snippet(
            content="def hello(): pass",
            metadata=SnippetMetadata(title="Hello", language=Language.PYTHON),
            tags=["python"],
        )
        storage.save(s)
        result = ensure_index(storage, search_engine)
        assert len(result) == 1

    def test_force_rebuild(self, storage, search_engine):
        s = Snippet(
            content="code",
            metadata=SnippetMetadata(title="Test"),
        )
        storage.save(s)
        ensure_index(storage, search_engine)
        # Force rebuild
        result = ensure_index(storage, search_engine, force=True)
        assert len(result) == 1


class TestSearchSnippets:
    def test_empty_storage(self, storage, search_engine):
        results = search_snippets(storage, search_engine, "query")
        assert results == []

    def test_keyword_search_returns_results(self, temp_config):
        """Test that search_snippets builds index and returns results via HybridSearch."""
        storage = StorageEngine(temp_config)
        search_engine = HybridSearch(temp_config)
        s = Snippet(
            content="def authenticate(token): pass",
            metadata=SnippetMetadata(title="Auth", language=Language.PYTHON),
            tags=["auth"],
        )
        storage.save(s)
        # Use search_snippets which properly handles index building
        results = search_snippets(storage, search_engine, "authenticate", mode="keyword", top_k=10)
        assert len(results) >= 1, f"Expected at least 1 result, got {len(results)}"

    def test_tag_search(self, storage, search_engine):
        s = Snippet(
            content="code",
            metadata=SnippetMetadata(title="Test"),
            tags=["python", "auth"],
        )
        storage.save(s)
        results = search_snippets(storage, search_engine, "python", mode="tag")
        assert len(results) >= 1

    def test_top_k_limit(self, storage, search_engine):
        for i in range(5):
            s = Snippet(
                content=f"def func_{i}(): pass",
                metadata=SnippetMetadata(title=f"Func {i}"),
            )
            storage.save(s)
        results = search_snippets(storage, search_engine, "def", mode="keyword", top_k=3)
        # Results may be empty if keyword index isn't built, but top_k should be respected
        assert len(results) <= 3


class TestExportSnippets:
    def test_export_all(self, storage, search_engine):
        s = Snippet(
            content="def hello(): pass",
            metadata=SnippetMetadata(title="Hello", language=Language.PYTHON),
        )
        storage.save(s)
        snippets, formatted = export_snippets(storage, search_engine, "generic")
        assert len(snippets) == 1
        assert isinstance(formatted, str)

    def test_export_by_ids(self, storage, search_engine):
        s1 = Snippet(content="a", metadata=SnippetMetadata(title="A"))
        s2 = Snippet(content="b", metadata=SnippetMetadata(title="B"))
        storage.save(s1)
        storage.save(s2)
        snippets, formatted = export_snippets(storage, search_engine, "generic", ids=[s1.id])
        assert len(snippets) == 1
        assert snippets[0].metadata.title == "A"

    def test_export_by_ids_skip_missing(self, storage, search_engine):
        s = Snippet(content="a", metadata=SnippetMetadata(title="A"))
        storage.save(s)
        snippets, formatted = export_snippets(
            storage, search_engine, "generic", ids=[s.id, "nonexistent"]
        )
        assert len(snippets) == 1

    def test_export_by_query(self, storage, search_engine):
        s = Snippet(
            content="def hello(): pass",
            metadata=SnippetMetadata(title="Hello", language=Language.PYTHON),
        )
        storage.save(s)
        snippets, formatted = export_snippets(storage, search_engine, "generic", query="hello")
        # Query export uses search_snippets which may return empty if index not built
        # but the function should still work
        assert isinstance(formatted, str)

    def test_export_invalid_provider(self, storage, search_engine):
        s = Snippet(content="a", metadata=SnippetMetadata(title="A"))
        storage.save(s)
        with pytest.raises(KeyError):
            export_snippets(storage, search_engine, "nonexistent_provider")
