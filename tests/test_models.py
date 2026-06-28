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

    def test_metadata_field_defaults(self):
        """New fields (framework, version, source_url, custom_tags) default correctly."""
        meta = SnippetMetadata(title="Test")
        assert meta.framework == ""
        assert meta.version == ""
        assert meta.source_url == ""
        assert meta.custom_tags == {}
        assert meta.author == ""
        assert meta.llm_optimized is False

    def test_metadata_with_all_fields(self):
        """Creating metadata with all fields populated works."""
        meta = SnippetMetadata(
            title="Full Snippet",
            description="Complete example",
            language=Language.PYTHON,
            source_url="https://github.com/example/repo",
            framework="fastapi",
            version="0.100+",
            author="dev",
            confidence="production",
            custom_tags={"priority": "high", "team": "backend"},
        )
        assert meta.framework == "fastapi"
        assert meta.version == "0.100+"
        assert meta.source_url == "https://github.com/example/repo"
        assert meta.custom_tags == {"priority": "high", "team": "backend"}

    def test_extra_fields_allowed(self):
        """ConfigDict(extra='allow') lets arbitrary keys through."""
        meta = SnippetMetadata(title="T")
        meta.random_future_field = "works"
        assert meta.random_future_field == "works"

    def test_backward_compat_missing_fields(self):
        """Loading a dict that omits new fields fills defaults (simulates old JSON)."""
        # Simulate what an old v0.2.x JSON file looks like
        old_data = {
            "title": "Old Snippet",
            "description": "From before v0.3",
            "language": "python",
        }
        meta = SnippetMetadata.model_validate(old_data)
        assert meta.title == "Old Snippet"
        assert meta.framework == ""
        assert meta.version == ""
        assert meta.source_url == ""
        assert meta.custom_tags == {}

    def test_backward_compat_unknown_fields(self):
        """Unknown fields in old data are silently accepted, not rejected."""
        data = {
            "title": "Future Snippet",
            "future_field": "some value",
        }
        meta = SnippetMetadata.model_validate(data)
        assert meta.title == "Future Snippet"
        assert meta.future_field == "some value"

    def test_snippet_backward_compat_roundtrip(self):
        """Simulate loading old JSON → save → reload cycle (storage round-trip)."""
        old_json = {
            "content": "print('hello')",
            "metadata": {
                "title": "Legacy",
                "description": "old",
                "language": "python",
            },
            "tags": ["demo"],
            "access_count": 5,
            "deleted": False,
        }
        # Load (Pydantic fills defaults for missing fields)
        s = Snippet.model_validate(old_json)
        assert s.metadata.framework == ""
        assert s.metadata.version == ""
        assert s.metadata.custom_tags == {}

        # Save (model_dump produces complete JSON)
        data = s.model_dump(mode="json")
        assert "framework" in data["metadata"]
        assert data["metadata"]["framework"] == ""

        # Reload from saved data
        s2 = Snippet.model_validate(data)
        assert s2.content == s.content
        assert s2.metadata.title == "Legacy"
        assert s2.metadata.framework == ""


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

    def test_content_empty_allowed(self):
        s = Snippet(content="", metadata=SnippetMetadata(title="Empty"))
        assert s.content == ""

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

    def test_to_search_text_includes_metadata_fields(self):
        """Framework, version, source_url, and custom_tags appear in search text."""
        s = Snippet(
            content="x",
            metadata=SnippetMetadata(
                title="T",
                framework="react",
                version="18.x",
                source_url="https://react.dev/docs",
                custom_tags={"env": "staging", "team": "frontend"},
            ),
        )
        text = s.to_search_text()
        assert "react" in text
        assert "18.x" in text
        assert "https://react.dev/docs" in text
        assert "env" in text
        assert "staging" in text
        assert "team" in text

    def test_to_search_text_omits_empty_metadata_fields(self):
        """Empty framework/version/source_url are not included in search text."""
        s = Snippet(
            content="x",
            metadata=SnippetMetadata(title="T", framework="", version=""),
        )
        text = s.to_search_text()
        # Should contain title and content but no empty framework/version lines
        lines = [line for line in text.split("\n") if line]
        assert any("T" in line for line in lines)
        assert len(lines) >= 1

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
