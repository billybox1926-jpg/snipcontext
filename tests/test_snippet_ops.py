"""Tests for snippet_ops domain logic — targeted coverage for uncovered lines."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from snipcontext.config.settings import Config, StorageConfig, reset_config
from snipcontext.core.models import Language, Snippet, SnippetMetadata
from snipcontext.core.snippet_ops import (
    add_snippet,
    auto_title,
    create_snippet,
    delete_snippet,
    edit_snippet,
    get_snippet,
    list_snippets,
    record_snippet_access,
    resolve_language,
)
from snipcontext.core.storage import SnippetNotFoundError, StorageEngine


@pytest.fixture
def temp_config():
    with tempfile.TemporaryDirectory() as tmp:
        config = Config(
            storage=StorageConfig(
                data_dir=Path(tmp),
                snippets_dir="snippets",
                index_dir="index",
            )
        )
        yield config
        reset_config()


@pytest.fixture
def storage(temp_config):
    return StorageEngine(temp_config)


@pytest.fixture
def saved_snippet(storage):
    s = Snippet(
        content="def hello():\n    print('hi')",
        metadata=SnippetMetadata(title="Hello", language=Language.PYTHON),
        tags=["python", "demo"],
    )
    storage.save(s)
    return s


class TestResolveLanguage:
    def test_explicit_language(self):
        assert resolve_language("python", "test", False, "") == "python"

    def test_from_file_extension(self):
        assert resolve_language("", "test", True, "/path/to/file.py") == "python"

    def test_from_file_unknown_extension(self):
        assert resolve_language("", "test", True, "/path/to/file.xyz") == ""

    def test_from_title_extension(self):
        assert resolve_language("", "my_snippet.js", False, "") == "javascript"

    def test_from_title_no_extension(self):
        assert resolve_language("", "my_snippet", False, "") == ""

    def test_from_file_dockerfile(self):
        assert resolve_language("", "test", True, "/path/to/Dockerfile") == "dockerfile"

    def test_from_file_tf(self):
        assert resolve_language("", "test", True, "/path/to/main.tf") == "terraform"


class TestAutoTitle:
    def test_first_line(self):
        assert auto_title("def hello():\n    pass") == "def hello():"

    def test_truncates_long_line(self):
        long_line = "x" * 100
        assert auto_title(long_line) == "x" * 50

    def test_empty_content(self):
        assert auto_title("") == "Untitled Snippet"

    def test_whitespace_only(self):
        assert auto_title("   \n  ") == "Untitled Snippet"


class TestCreateSnippet:
    def test_empty_content_raises(self):
        with pytest.raises(ValueError, match="empty"):
            create_snippet("", "title", "desc", "python", [])

    def test_whitespace_only_content_raises(self):
        with pytest.raises(ValueError, match="empty"):
            create_snippet("   ", "title", "desc", "python", [])

    def test_invalid_language_becomes_unknown(self):
        s = create_snippet("code", "title", "desc", "not_a_real_language", [])
        assert s.metadata.language == Language.UNKNOWN

    def test_encrypted_snippet(self):
        s = create_snippet(
            "",
            "title",
            "desc",
            "python",
            ["tag"],
            encrypt=True,
            encrypted_content="encrypted-blob",
        )
        assert s.content == ""
        assert s.encrypted_content == "encrypted-blob"

    def test_normal_snippet(self):
        s = create_snippet("code", "title", "desc", "python", ["tag"])
        assert s.content == "code"
        assert s.metadata.title == "title"
        assert s.metadata.language == Language.PYTHON
        assert "tag" in s.tags


class TestAddSnippet:
    def test_add_and_retrieve(self, storage):
        s = add_snippet(storage, "code", "title", "desc", "python", ["tag"])
        assert s.id is not None
        loaded = storage.get(s.id)
        assert loaded.content == "code"


class TestGetSnippet:
    def test_get_by_full_id(self, storage, saved_snippet):
        result = get_snippet(storage, saved_snippet.id)
        assert result.id == saved_snippet.id

    def test_get_by_prefix(self, storage, saved_snippet):
        prefix = saved_snippet.id[:8]
        result = get_snippet(storage, prefix)
        assert result.id == saved_snippet.id

    def test_get_not_found(self, storage):
        with pytest.raises(SnippetNotFoundError):
            get_snippet(storage, "nonexistent")

    def test_get_ambiguous_prefix(self, storage):
        s1 = Snippet(content="a", metadata=SnippetMetadata(title="A"))
        s2 = Snippet(content="b", metadata=SnippetMetadata(title="B"))
        storage.save(s1)
        storage.save(s2)
        # If they share a prefix, should raise ValueError
        common = s1.id[:4]
        if s2.id[:4] == common:
            with pytest.raises(ValueError, match="Multiple"):
                get_snippet(storage, common)


class TestListSnippets:
    def test_filter_by_tag(self, storage):
        s1 = Snippet(content="a", metadata=SnippetMetadata(title="A"), tags=["python"])
        s2 = Snippet(content="b", metadata=SnippetMetadata(title="B"), tags=["javascript"])
        storage.save(s1)
        storage.save(s2)
        results = list_snippets(storage, tag="python")
        assert len(results) == 1
        assert results[0].metadata.title == "A"

    def test_filter_by_language(self, storage):
        s1 = Snippet(
            content="a",
            metadata=SnippetMetadata(title="A", language=Language.PYTHON),
        )
        s2 = Snippet(
            content="b",
            metadata=SnippetMetadata(title="B", language=Language.JAVASCRIPT),
        )
        storage.save(s1)
        storage.save(s2)
        results = list_snippets(storage, language="python")
        assert len(results) == 1
        assert results[0].metadata.title == "A"

    def test_sort_by_title(self, storage):
        s1 = Snippet(content="a", metadata=SnippetMetadata(title="Zebra"))
        s2 = Snippet(content="b", metadata=SnippetMetadata(title="Apple"))
        storage.save(s1)
        storage.save(s2)
        results = list_snippets(storage, sort="title")
        assert results[0].metadata.title == "Apple"
        assert results[1].metadata.title == "Zebra"

    def test_sort_by_created(self, storage):
        s1 = Snippet(content="a", metadata=SnippetMetadata(title="First"))
        s2 = Snippet(content="b", metadata=SnippetMetadata(title="Second"))
        storage.save(s1)
        storage.save(s2)
        results = list_snippets(storage, sort="created")
        assert len(results) == 2

    def test_sort_by_access(self, storage):
        s1 = Snippet(content="a", metadata=SnippetMetadata(title="Low"))
        s2 = Snippet(content="b", metadata=SnippetMetadata(title="High"))
        s1.record_access()
        s1.record_access()
        storage.save(s1)
        storage.save(s2)
        results = list_snippets(storage, sort="access")
        assert results[0].metadata.title == "Low"


class TestEditSnippet:
    def test_edit_content(self, storage, saved_snippet):
        updated = edit_snippet(storage, saved_snippet.id, content="new content")
        assert updated.content == "new content"

    def test_edit_title(self, storage, saved_snippet):
        updated = edit_snippet(storage, saved_snippet.id, title="New Title")
        assert updated.metadata.title == "New Title"

    def test_edit_description(self, storage, saved_snippet):
        updated = edit_snippet(storage, saved_snippet.id, description="New desc")
        assert updated.metadata.description == "New desc"

    def test_edit_language(self, storage, saved_snippet):
        updated = edit_snippet(storage, saved_snippet.id, language="javascript")
        assert updated.metadata.language == Language.JAVASCRIPT

    def test_edit_invalid_language(self, storage, saved_snippet):
        updated = edit_snippet(storage, saved_snippet.id, language="not_a_language")
        assert updated.metadata.language == Language.UNKNOWN

    def test_edit_source(self, storage, saved_snippet):
        updated = edit_snippet(storage, saved_snippet.id, source="https://example.com")
        assert updated.metadata.source_url == "https://example.com"

    def test_edit_framework(self, storage, saved_snippet):
        updated = edit_snippet(storage, saved_snippet.id, framework="react")
        assert updated.metadata.framework == "react"

    def test_edit_version(self, storage, saved_snippet):
        updated = edit_snippet(storage, saved_snippet.id, version="1.0.0")
        assert updated.metadata.version == "1.0.0"

    def test_edit_custom_tags(self, storage, saved_snippet):
        updated = edit_snippet(storage, saved_snippet.id, custom_tags={"author": "test"})
        assert updated.metadata.custom_tags["author"] == "test"

    def test_edit_add_tags(self, storage, saved_snippet):
        updated = edit_snippet(storage, saved_snippet.id, add_tags=["newtag"])
        assert "newtag" in updated.tags

    def test_edit_remove_tags(self, storage, saved_snippet):
        updated = edit_snippet(storage, saved_snippet.id, remove_tags=["python"])
        assert "python" not in updated.tags

    def test_edit_preserves_unspecified_fields(self, storage, saved_snippet):
        original_desc = saved_snippet.metadata.description
        updated = edit_snippet(storage, saved_snippet.id, title="New Title")
        assert updated.metadata.description == original_desc


class TestDeleteSnippet:
    def test_delete(self, storage, saved_snippet):
        result = delete_snippet(storage, saved_snippet.id)
        assert result.id == saved_snippet.id
        assert not storage.exists(saved_snippet.id)

    def test_delete_not_found(self, storage):
        with pytest.raises(SnippetNotFoundError):
            delete_snippet(storage, "nonexistent")


class TestRecordSnippetAccess:
    def test_record_access(self, storage, saved_snippet):
        before = saved_snippet.access_count
        record_snippet_access(storage, saved_snippet)
        loaded = storage.get(saved_snippet.id)
        assert loaded.access_count == before + 1
