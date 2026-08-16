"""StorageEngine tests with temporary directories."""
import json
from datetime import datetime, timezone
from pathlib import Path
import tempfile

import pytest
from unittest.mock import MagicMock, patch

from snipcontext.config.settings import Config, StorageConfig
from snipcontext.core.models import Language, Snippet
from snipcontext.core.storage import StorageEngine, StorageError


@pytest.fixture
def tmp_dir():
    """Provide a clean temporary directory for each test."""
    return Path(tempfile.mkdtemp())


@pytest.fixture
def storage(tmp_dir):
    """Provide a StorageEngine with isolated temp storage."""
    # Create config with explicit storage config
    storage_config = StorageConfig(data_dir=tmp_dir, snippets_dir="snippets", index_dir="index")
    config = Config(
        storage=storage_config,
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
    # Ensure temp subdirs exist
    (tmp_dir / "snippets").mkdir(parents=True, exist_ok=True)
    (tmp_dir / "index").mkdir(parents=True, exist_ok=True)
    return StorageEngine(config)


@pytest.fixture
def sample_snippet():
    return Snippet(
        id="test-123",
        title="Test Snippet",
        content="This is test content.",
        language=Language.PYTHON,
        tags=["test", "python"],
        created_at=datetime.now(timezone.utc),
    )


def test_save_creates_file(storage, sample_snippet):
    """save() creates a JSON file for the snippet."""
    path = storage.save(sample_snippet)
    assert path.exists()
    assert path.suffix == ".json"


def test_save_roundtrip(storage, sample_snippet):
    """save() followed by get() returns equal snippet."""
    storage.save(sample_snippet)
    loaded = storage.get(sample_snippet.id)
    assert loaded.id == sample_snippet.id
    assert loaded.title == sample_snippet.title
    assert loaded.content == sample_snippet.content
    assert loaded.language == sample_snippet.language
    assert loaded.tags == sample_snippet.tags


def test_get_nonexistent_raises_storage_error(storage):
    """get() raises StorageError for missing snippet."""
    with pytest.raises(StorageError) as exc_info:
        storage.get("nonexistent-id")
    assert exc_info.value.code == "not_found"


def test_delete_removes_file(storage, sample_snippet):
    """delete() removes the snippet file."""
    storage.save(sample_snippet)
    assert storage.delete(sample_snippet.id) is True
    assert not storage.exists(sample_snippet.id)


def test_delete_nonexistent_returns_false(storage):
    """delete() returns False for missing snippet."""
    assert storage.delete("nonexistent-id") is False


def test_exists_returns_correct_boolean(storage, sample_snippet):
    """exists() returns True if snippet exists, False otherwise."""
    assert storage.exists(sample_snippet.id) is False
    storage.save(sample_snippet)
    assert storage.exists(sample_snippet.id) is True


def test_list_all_returns_all_snippets(storage):
    """list_all() returns all saved snippets."""
    now = datetime.now(timezone.utc)
    for i in range(3):
        snippet = Snippet(
            id=f"snippet-{i}",
            title=f"Title {i}",
            content=f"Content {i}",
            language=Language.MARKDOWN,
            tags=[],
            created_at=now,
        )
        storage.save(snippet)
    
    all_snippets = storage.list_all()
    assert len(all_snippets) == 3


def test_count_returns_total(storage):
    """count() returns the number of stored snippets."""
    now = datetime.now(timezone.utc)
    for i in range(5):
        snippet = Snippet(
            id=f"count-{i}",
            title=f"Title {i}",
            content=f"Content {i}",
            language=Language.MARKDOWN,
            tags=[],
            created_at=now,
        )
        storage.save(snippet)
    
    assert storage.count() == 5


def test_iter_all_skips_corrupted_files(storage):
    """iter_all() skips corrupted JSON files."""
    # Create a valid snippet
    now = datetime.now(timezone.utc)
    valid = Snippet(
        id="valid",
        title="Valid",
        content="Valid content",
        language=Language.MARKDOWN,
        tags=[],
        created_at=now,
    )
    storage.save(valid)
    
    # Create a corrupted file
    corrupt_path = storage.snippets_dir / "corrupt.json"
    corrupt_path.write_text("not valid json {{{")
    
    # iter_all should skip the corrupted file
    snippets = list(storage.iter_all())
    assert len(snippets) == 1
    assert snippets[0].id == "valid"


def test_find_by_tag_returns_matching(storage):
    """find_by_tag() returns snippets with matching tag."""
    now = datetime.now(timezone.utc)
    s1 = Snippet(
        id="tagged-1",
        title="Tagged",
        content="Content",
        language=Language.MARKDOWN,
        tags=["python", "cli"],
        created_at=now,
    )
    s2 = Snippet(
        id="tagged-2",
        title="Also Tagged",
        content="Content",
        language=Language.MARKDOWN,
        tags=["javascript"],
        created_at=now,
    )
    storage.save(s1)
    storage.save(s2)
    
    results = storage.find_by_tag("python")
    assert len(results) == 1
    assert results[0].id == "tagged-1"


def test_get_all_tags_returns_unique_sorted(storage):
    """get_all_tags() returns sorted unique tags."""
    now = datetime.now(timezone.utc)
    s1 = Snippet(
        id="tag-1",
        title="T1",
        content="C1",
        language=Language.MARKDOWN,
        tags=["python", "cli"],
        created_at=now,
    )
    s2 = Snippet(
        id="tag-2",
        title="T2",
        content="C2",
        language=Language.MARKDOWN,
        tags=["python", "web"],
        created_at=now,
    )
    storage.save(s1)
    storage.save(s2)
    
    tags = storage.get_all_tags()
    assert tags == ["cli", "python", "web"]


def test_get_stats_returns_correct_counts(storage):
    """get_stats() returns correct statistics."""
    now = datetime.now(timezone.utc)
    for i in range(3):
        snippet = Snippet(
            id=f"stats-{i}",
            title=f"Title {i}",
            content=f"Content {i}",
            language=Language.PYTHON if i == 0 else Language.MARKDOWN,
            tags=["python"] if i == 0 else ["markdown"],
            created_at=now,
        )
        storage.save(snippet)
    
    stats = storage.get_stats()
    assert stats["total_snippets"] == 3
    assert stats["total_tags"] == 2


def test_write_and_read_storage_version(storage):
    """write_storage_version() and read_storage_version() roundtrip."""
    storage.write_storage_version()
    version = storage.read_storage_version()
    assert version is not None
    assert len(version) > 0


def test_read_storage_version_missing_returns_default(tmp_dir):
    """read_storage_version() returns '0.0.0' when file missing."""
    # Create a fresh storage engine without writing version
    storage_config = StorageConfig(data_dir=tmp_dir, snippets_dir="snippets", index_dir="index")
    config = Config(
        storage=storage_config,
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
    (tmp_dir / "snippets").mkdir(parents=True, exist_ok=True)
    (tmp_dir / "index").mkdir(parents=True, exist_ok=True)
    engine = StorageEngine(config)
    version = engine.read_storage_version()
    assert version == "0.0.0"


def test_export_all_creates_file(storage):
    """export_all() creates a JSON file with all snippets."""
    now = datetime.now(timezone.utc)
    snippet = Snippet(
        id="export-1",
        title="Export",
        content="Content",
        language=Language.MARKDOWN,
        tags=[],
        created_at=now,
    )
    storage.save(snippet)
    
    output_path = storage.index_dir / "export.json"
    result = storage.export_all(output_path)
    assert result.exists()
    
    with open(result) as f:
        data = json.load(f)
    assert data["count"] == 1


def test_import_file_loads_snippets(storage):
    """import_file() loads snippets from JSON export."""
    now = datetime.now(timezone.utc)
    snippet = Snippet(
        id="import-1",
        title="Import",
        content="Content",
        language=Language.MARKDOWN,
        tags=[],
        created_at=now,
    )
    storage.save(snippet)
    
    # Export and re-import
    export_path = storage.index_dir / "import_test.json"
    storage.export_all(export_path)
    
    # Delete original
    storage.delete("import-1")
    assert storage.count() == 0
    
    # Import
    count = storage.import_file(export_path)
    assert count == 1
    assert storage.exists("import-1")


def test_vacuum_removes_orphaned_files(storage):
    """vacuum() removes files with invalid snippet IDs."""
    now = datetime.now(timezone.utc)
    valid = Snippet(
        id="valid-vacuum",
        title="Valid",
        content="Content",
        language=Language.MARKDOWN,
        tags=[],
        created_at=now,
    )
    storage.save(valid)
    
    # Create orphaned file with invalid schema (content must be a string, not a number)
    orphan_path = storage.snippets_dir / "orphan.json"
    orphan_path.write_text(json.dumps({"id": "orphan", "content": 123}))
    
    freed = storage.vacuum()
    assert freed > 0
    assert not orphan_path.exists()
    assert storage.exists("valid-vacuum")


def test_reindex_all_rewrites_files(storage):
    """reindex_all() rewrites all snippet files."""
    now = datetime.now(timezone.utc)
    snippet = Snippet(
        id="reindex-1",
        title="Reindex",
        content="Content",
        language=Language.MARKDOWN,
        tags=[],
        created_at=now,
    )
    storage.save(snippet)
    
    count = storage.reindex_all()
    assert count == 1
    assert storage.exists("reindex-1")
