"""Tests for the storage engine."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from snipcontext.config.settings import Config, StorageConfig, reset_config
from snipcontext.core.models import Language, Snippet, SnippetMetadata
from snipcontext.core.storage import (
    EncryptionError,
    IndexCorruptedError,
    MissingIndexError,
    SnippetNotFoundError,
    StorageEngine,
    StorageError,
)


@pytest.fixture
def temp_config():
    """Provide a config using a temporary directory."""
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
def sample_snippet():
    return Snippet(
        content="def hello():\n    print('Hello, World!')",
        metadata=SnippetMetadata(
            title="Hello World",
            description="A simple greeting function",
            language=Language.PYTHON,
        ),
        tags=["python", "demo", "beginner"],
    )


@pytest.fixture
def encrypted_storage(temp_config, monkeypatch):
    """Provide a StorageEngine with Fernet encryption enabled."""
    config = temp_config
    config.encryption.enabled = True
    monkeypatch.setenv("SNIPCONTEXT_ENCRYPTION_PASSPHRASE", "test-passphrase-for-unit-tests")
    return StorageEngine(config)


class TestEncryption:
    """Tests for content encryption/decryption."""

    pytest.importorskip("cryptography")

    def test_roundtrip(self, encrypted_storage):
        plaintext = "hello, world"
        ciphertext = encrypted_storage.encrypt_content(plaintext)
        assert encrypted_storage.decrypt_content(ciphertext) == plaintext

    def test_different_plaintexts_produce_different_ciphertexts(self, encrypted_storage):
        ct1 = encrypted_storage.encrypt_content("hello")
        ct2 = encrypted_storage.encrypt_content("world")
        assert ct1 != ct2

    def test_same_plaintext_produces_different_ciphertexts(self, encrypted_storage):
        ct1 = encrypted_storage.encrypt_content("hello")
        ct2 = encrypted_storage.encrypt_content("hello")
        assert ct1 != ct2

    def test_wrong_key_fails(self, temp_config, monkeypatch):
        config = temp_config
        config.encryption.enabled = True

        monkeypatch.setenv("SNIPCONTEXT_ENCRYPTION_PASSPHRASE", "passphrase-a")
        storage_a = StorageEngine(config)
        encrypted = storage_a.encrypt_content("secret")

        monkeypatch.setenv("SNIPCONTEXT_ENCRYPTION_PASSPHRASE", "passphrase-b")
        storage_b = StorageEngine(config)
        with pytest.raises(EncryptionError):
            storage_b.decrypt_content(encrypted)

    def test_empty_string_roundtrip(self, encrypted_storage):
        ciphertext = encrypted_storage.encrypt_content("")
        assert encrypted_storage.decrypt_content(ciphertext) == ""

    def test_unicode_roundtrip(self, encrypted_storage):
        plaintext = "你好 🚀 émoji"
        ciphertext = encrypted_storage.encrypt_content(plaintext)
        assert encrypted_storage.decrypt_content(ciphertext) == plaintext


class TestStorageCRUD:
    """Tests for basic CRUD operations."""

    def test_save_and_get(self, temp_config, sample_snippet):
        storage = StorageEngine(temp_config)
        path = storage.save(sample_snippet)

        assert path.exists()
        assert path.name == f"{sample_snippet.id}.json"

        loaded = storage.get(sample_snippet.id)
        assert loaded.metadata.title == "Hello World"
        assert loaded.content == sample_snippet.content
        assert loaded.tags == ["beginner", "demo", "python"]

    def test_save_creates_directories(self, temp_config):
        storage = StorageEngine(temp_config)
        assert storage.snippets_dir.exists()
        assert storage.index_dir.exists()

    def test_get_not_found(self, temp_config):
        storage = StorageEngine(temp_config)
        with pytest.raises(SnippetNotFoundError):
            storage.get("nonexistent-id")

    def test_delete(self, temp_config, sample_snippet):
        storage = StorageEngine(temp_config)
        storage.save(sample_snippet)
        assert storage.exists(sample_snippet.id)

        result = storage.delete(sample_snippet.id)
        assert result is True
        assert not storage.exists(sample_snippet.id)

    def test_delete_nonexistent(self, temp_config):
        storage = StorageEngine(temp_config)
        result = storage.delete("nonexistent")
        assert result is False

    def test_embedding_not_in_json(self, temp_config, sample_snippet):
        storage = StorageEngine(temp_config)
        sample_snippet.embedding = [0.1, 0.2, 0.3]
        storage.save(sample_snippet)

        raw = json.loads(storage._snippet_path(sample_snippet.id).read_text())
        assert "embedding" not in raw


class TestStorageBulk:
    """Tests for bulk operations."""

    def test_iter_all(self, temp_config):
        storage = StorageEngine(temp_config)
        for i in range(5):
            s = Snippet(
                content=f"code_{i}",
                metadata=SnippetMetadata(title=f"Snippet {i}"),
                tags=[f"tag{i}"],
            )
            storage.save(s)

        all_snippets = list(storage.iter_all())
        assert len(all_snippets) == 5

    def test_count(self, temp_config):
        storage = StorageEngine(temp_config)
        assert storage.count() == 0

        storage.save(Snippet(content="a", metadata=SnippetMetadata(title="A")))
        assert storage.count() == 1

    def test_empty_storage(self, temp_config):
        storage = StorageEngine(temp_config)
        assert list(storage.iter_all()) == []
        assert storage.count() == 0


class TestStorageTags:
    """Tests for tag-based operations."""

    def test_find_by_tag(self, temp_config):
        storage = StorageEngine(temp_config)
        s1 = Snippet(content="x", metadata=SnippetMetadata(title="A"), tags=["python", "web"])
        s2 = Snippet(content="y", metadata=SnippetMetadata(title="B"), tags=["python", "cli"])
        s3 = Snippet(content="z", metadata=SnippetMetadata(title="C"), tags=["web"])
        for s in [s1, s2, s3]:
            storage.save(s)

        py_results = storage.find_by_tag("python")
        assert len(py_results) == 2
        assert all("python" in s.tags for s in py_results)

    def test_get_all_tags(self, temp_config):
        storage = StorageEngine(temp_config)
        s1 = Snippet(content="x", metadata=SnippetMetadata(title="A"), tags=["a", "b"])
        s2 = Snippet(content="y", metadata=SnippetMetadata(title="B"), tags=["b", "c"])
        storage.save(s1)
        storage.save(s2)

        tags = storage.get_all_tags()
        assert tags == ["a", "b", "c"]


class TestStorageStats:
    """Tests for statistics."""

    def test_empty_stats(self, temp_config):
        storage = StorageEngine(temp_config)
        stats = storage.get_stats()
        assert stats["total_snippets"] == 0

    def test_populated_stats(self, temp_config):
        storage = StorageEngine(temp_config)
        s1 = Snippet(
            content="x", metadata=SnippetMetadata(title="A", language=Language.PYTHON), tags=["py"]
        )
        s2 = Snippet(
            content="y",
            metadata=SnippetMetadata(title="B", language=Language.PYTHON),
            tags=["py", "web"],
        )
        storage.save(s1)
        storage.save(s2)

        stats = storage.get_stats()
        assert stats["total_snippets"] == 2
        assert stats["total_tags"] == 2
        assert stats["languages"] == {"python": 2}


class TestStorageImportExport:
    """Tests for import/export."""

    def test_export_all(self, temp_config):
        storage = StorageEngine(temp_config)
        s = Snippet(content="hello", metadata=SnippetMetadata(title="H"))
        storage.save(s)

        with tempfile.TemporaryDirectory() as tmp:
            export_path = Path(tmp) / "export.json"
            result = storage.export_all(export_path)
            assert result.exists()
            data = json.loads(result.read_text())
            assert data["count"] == 1

    def test_import_file(self, temp_config):
        storage = StorageEngine(temp_config)
        export_data = {
            "snippets": [
                {
                    "content": "def test(): pass",
                    "metadata": {"title": "Test Func", "language": "python"},
                    "tags": ["test"],
                }
            ],
            "count": 1,
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(export_data, f)
            f.flush()
            count = storage.import_file(Path(f.name))

        assert count == 1
        assert storage.count() == 1

    def test_import_file_not_found(self, temp_config):
        storage = StorageEngine(temp_config)
        with pytest.raises(StorageError):
            storage.import_file(Path("/nonexistent/file.json"))


class TestStorageExceptions:
    """Tests for storage exception classes."""

    def test_storage_error(self):
        with pytest.raises(StorageError):
            raise StorageError("test error")

    def test_snippet_not_found_error(self):
        with pytest.raises(SnippetNotFoundError):
            raise SnippetNotFoundError("not found")

    def test_index_corrupted_error_without_cause(self):
        err = IndexCorruptedError("vector", "/path/to/index")
        assert err.index_type == "vector"
        assert err.path == "/path/to/index"
        assert err.original_error is None
        assert "vector" in str(err)
        assert "/path/to/index" in str(err)

    def test_index_corrupted_error_with_cause(self):
        cause = RuntimeError("disk full")
        err = IndexCorruptedError("keyword", "/path/to/index", original_error=cause)
        assert err.original_error is cause
        assert "disk full" in str(err)

    def test_missing_index_error(self):
        err = MissingIndexError("vector", "/path/to/index")
        assert err.index_type == "vector"
        assert err.path == "/path/to/index"
        assert "vector" in str(err)
        assert "/path/to/index" in str(err)

    def test_encryption_error_operation_only(self):
        err = EncryptionError("encrypt")
        assert err.operation == "encrypt"
        assert err.snippet_id is None
        assert err.original_error is None
        assert "encrypt" in str(err)

    def test_encryption_error_with_snippet_id(self):
        err = EncryptionError("decrypt", snippet_id="abc123")
        assert err.snippet_id == "abc123"
        assert "abc123" in str(err)

    def test_encryption_error_with_original_error(self):
        cause = ValueError("bad key")
        err = EncryptionError("encrypt", original_error=cause)
        assert err.original_error is cause
        assert "bad key" in str(err)


class TestStorageProperties:
    """Tests for storage engine properties."""

    def test_index_dir_property(self, temp_config):
        storage = StorageEngine(temp_config)
        assert storage.index_dir.exists()

    def test_deleted_ids_property(self, temp_config):
        storage = StorageEngine(temp_config)
        assert storage.deleted_ids == set()

    def test_mark_deleted(self, temp_config, sample_snippet):
        storage = StorageEngine(temp_config)
        storage.save(sample_snippet)
        storage.mark_deleted(sample_snippet.id)
        assert sample_snippet.id in storage.deleted_ids

    def test_exists(self, temp_config, sample_snippet):
        storage = StorageEngine(temp_config)
        assert not storage.exists(sample_snippet.id)
        storage.save(sample_snippet)
        assert storage.exists(sample_snippet.id)

    def test_exists_nonexistent(self, temp_config):
        storage = StorageEngine(temp_config)
        assert not storage.exists("nonexistent-id")


class TestStorageGetTags:
    """Tests for tag retrieval."""

    def test_get_tags(self, temp_config):
        storage = StorageEngine(temp_config)
        s = Snippet(
            content="code",
            metadata=SnippetMetadata(title="Test"),
            tags=["python", "web"],
        )
        storage.save(s)
        tags = storage.get_tags(s.id)
        assert "python" in tags
        assert "web" in tags

    def test_get_all_tags_empty(self, temp_config):
        storage = StorageEngine(temp_config)
        assert storage.get_all_tags() == []

    def test_get_all_tags_dedup(self, temp_config):
        storage = StorageEngine(temp_config)
        s1 = Snippet(content="a", metadata=SnippetMetadata(title="A"), tags=["shared", "a"])
        s2 = Snippet(content="b", metadata=SnippetMetadata(title="B"), tags=["shared", "b"])
        storage.save(s1)
        storage.save(s2)
        tags = storage.get_all_tags()
        assert tags == ["a", "b", "shared"]


class TestStorageReindex:
    """Tests for reindex and vacuum operations."""

    def test_reindex_all(self, temp_config):
        storage = StorageEngine(temp_config)
        s = Snippet(content="code", metadata=SnippetMetadata(title="Test"))
        storage.save(s)
        count = storage.reindex_all()
        assert count == 1

    def test_reindex_empty(self, temp_config):
        storage = StorageEngine(temp_config)
        count = storage.reindex_all()
        assert count == 0

    def test_vacuum_no_orphans(self, temp_config):
        storage = StorageEngine(temp_config)
        s = Snippet(content="code", metadata=SnippetMetadata(title="Test"))
        storage.save(s)
        freed = storage.vacuum()
        assert freed == 0

    def test_vacuum_with_orphan(self, temp_config):
        storage = StorageEngine(temp_config)
        # Create a valid snippet
        s = Snippet(content="code", metadata=SnippetMetadata(title="Test"))
        storage.save(s)
        # Create an orphaned file
        orphan_path = storage.snippets_dir / "orphan.json"
        orphan_path.write_text('{"not": "valid"}')
        freed = storage.vacuum()
        assert freed > 0
        assert not orphan_path.exists()


class TestStorageImportEdgeCases:
    """Tests for import edge cases."""

    def test_import_list_format(self, temp_config):
        storage = StorageEngine(temp_config)
        import_data = [
            {
                "content": "def test(): pass",
                "metadata": {"title": "Test", "language": "python"},
                "tags": ["test"],
            }
        ]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(import_data, f)
            f.flush()
            count = storage.import_file(Path(f.name))
        assert count == 1

    def test_import_skips_invalid_items(self, temp_config):
        storage = StorageEngine(temp_config)
        import_data = {
            "snippets": [
                {
                    "content": "valid code",
                    "metadata": {"title": "Valid"},
                    "tags": [],
                },
                {"invalid": "no content field"},
            ],
            "count": 2,
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(import_data, f)
            f.flush()
            count = storage.import_file(Path(f.name))
        assert count == 1

    def test_import_empty_list(self, temp_config):
        storage = StorageEngine(temp_config)
        import_data = {"snippets": [], "count": 0}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(import_data, f)
            f.flush()
            count = storage.import_file(Path(f.name))
        assert count == 0

    def test_import_malformed_json(self, temp_config):
        storage = StorageEngine(temp_config)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("not valid json{{{")
            f.flush()
            with pytest.raises(StorageError):
                storage.import_file(Path(f.name))


class TestStorageEncryptionErrors:
    """Tests for encryption error paths."""

    pytest.importorskip("cryptography")

    def test_encrypt_without_encryption_enabled(self, temp_config, monkeypatch):
        """Test that encryption raises when not enabled."""
        config = temp_config
        config.encryption.enabled = False
        storage = StorageEngine(config)
        with pytest.raises(EncryptionError):
            storage.encrypt_content("test")

    def test_decrypt_without_encryption_enabled(self, temp_config):
        """Test that decryption raises when not enabled."""
        config = temp_config
        config.encryption.enabled = False
        storage = StorageEngine(config)
        with pytest.raises(EncryptionError):
            storage.decrypt_content("dGVzdA==")

    def test_decrypt_invalid_token(self, encrypted_storage):
        """Test that decrypting invalid data raises EncryptionError."""
        with pytest.raises(EncryptionError):
            encrypted_storage.decrypt_content("not-valid-base64!!!")

