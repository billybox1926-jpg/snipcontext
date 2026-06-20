"""Tests for core data models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError
from snipcontext.core.models import (
    Language,
    SearchMode,
    SearchResult,
    Snippet,
    SnippetMetadata,
    SnippetVersion,
)


class TestSnippetMetadata:
    """Tests for SnippetMetadata model."""

    def test_valid_creation(self):
        meta = SnippetMetadata(title="Test Snippet")
        assert meta.title == "Test Snippet"
        assert meta.description == ""
        assert meta.language == Language.UNKNOWN

    def test_title_required(self):
        with pytest.raises(ValidationError):
            SnippetMetadata()  # title is required

    def test_title_too_long(self):
        with pytest.raises(ValidationError):
            SnippetMetadata(title="x" * 201)

    def test_confidence_levels(self):
        for level in ["draft", "reviewed", "production", "reference"]:
            meta = SnippetMetadata(title="T", confidence=level)
            assert meta.confidence == level


class TestSnippetVersion:
    """Tests for SnippetVersion model."""

    def test_auto_id(self):
        v = SnippetVersion(content="print('hello')")
        assert len(v.id) == 22

    def test_auto_hash(self):
        v = SnippetVersion(content="print('hello')")
        assert len(v.change_hash) == 16
        assert v.change_hash != ""

    def test_hash_computed(self):
        v = SnippetVersion(content="x")
        assert len(v.change_hash) == 16
        v2 = SnippetVersion(content="x", change_hash="customhash1234")
        assert v2.change_hash == "customhash1234"


class TestSnippet:
    """Tests for Snippet model."""

    def test_minimal_creation(self):
        s = Snippet(content="print('hello')", metadata=SnippetMetadata(title="Hello"))
        assert s.content == "print('hello')"
        assert s.metadata.title == "Hello"
        assert len(s.id) == 22

    def test_content_required(self):
        with pytest.raises(ValidationError):
            Snippet(content="", metadata=SnippetMetadata(title="Empty"))

    def test_tags_normalized(self):
        s = Snippet(
            content="x",
            metadata=SnippetMetadata(title="T"),
            tags=["PYTHON", " auth ", "web", "python"],
        )
        assert s.tags == ["auth", "python", "web"]

    def test_content_hash(self):
        s = Snippet(content="hello", metadata=SnippetMetadata(title="T"))
        assert len(s.content_hash) == 16

    def test_tag_line(self):
        s = Snippet(content="x", metadata=SnippetMetadata(title="T"), tags=["a", "b"])
        assert s.tag_line == "#a, #b"

    def test_empty_tag_line(self):
        s = Snippet(content="x", metadata=SnippetMetadata(title="T"), tags=[])
        assert s.tag_line == ""

    def test_bump_version(self):
        s = Snippet(content="v1", metadata=SnippetMetadata(title="T"))
        s.bump_version("Initial version")
        assert len(s.versions) == 1
        assert s.versions[0].content == "v1"
        assert "Initial version" in s.versions[0].change_message

    def test_version_limit(self):
        s = Snippet(content="x", metadata=SnippetMetadata(title="T"))
        for i in range(55):
            s.bump_version(f"v{i}")
        assert len(s.versions) <= 50

    def test_merge_tags(self):
        s = Snippet(content="x", metadata=SnippetMetadata(title="T"), tags=["a"])
        s.merge_tags(["b", "A"])
        assert s.tags == ["a", "b"]

    def test_to_search_text(self):
        s = Snippet(
            content="def hello(): pass",
            metadata=SnippetMetadata(title="Hello Func", description="A greeting"),
            tags=["python", "demo"],
        )
        text = s.to_search_text()
        assert "Hello Func" in text
        assert "A greeting" in text
        assert "def hello(): pass" in text
        assert "python" in text

    def test_access_tracking(self):
        s = Snippet(content="x", metadata=SnippetMetadata(title="T"))
        assert s.access_count == 0
        s.record_access()
        assert s.access_count == 1

    def test_touch(self):
        import time

        s = Snippet(content="x", metadata=SnippetMetadata(title="T"))
        old = s.updated_at
        time.sleep(0.01)
        s.touch()
        assert s.updated_at > old

    def test_serialization_excludes_embedding(self):
        s = Snippet(content="x", metadata=SnippetMetadata(title="T"))
        s.embedding = [0.1, 0.2, 0.3]
        data = s.model_dump(mode="json")
        assert "embedding" not in data


class TestSearchResult:
    """Tests for SearchResult model."""

    def test_creation(self):
        s = Snippet(content="x", metadata=SnippetMetadata(title="T"))
        r = SearchResult(snippet=s, score=0.95, matched_by="semantic")
        assert r.score == 0.95
        assert r.matched_by == "semantic"
        assert r.id == s.id

    def test_score_bounds(self):
        s = Snippet(content="x", metadata=SnippetMetadata(title="T"))
        with pytest.raises(ValidationError):
            SearchResult(snippet=s, score=1.5, matched_by="semantic")
        with pytest.raises(ValidationError):
            SearchResult(snippet=s, score=-0.1, matched_by="semantic")


class TestLanguageEnum:
    """Tests for Language enum."""

    def test_all_values(self):
        assert Language.PYTHON.value == "python"
        assert Language.UNKNOWN.value == "unknown"

    def test_from_string(self):
        assert Language("python") == Language.PYTHON
        assert Language("rust") == Language.RUST


class TestSearchModeEnum:
    """Tests for SearchMode enum."""

    def test_values(self):
        assert SearchMode.SEMANTIC.value == "semantic"
        assert SearchMode.HYBRID.value == "hybrid"
        assert SearchMode.TAG.value == "tag"
