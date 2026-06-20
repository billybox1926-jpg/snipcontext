"""Unit tests for incremental indexing in HybridSearch and storage mark_deleted."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path
from unittest.mock import MagicMock, patch


class _Snippet:
    def __init__(self, snippet_id: str, deleted: bool = False) -> None:
        self.id = snippet_id
        self.deleted = deleted


# ---------- HybridSearch incremental methods ----------


def test_add_snippet_calls_vector_index_add_vector() -> None:
    from snipcontext.core.search import HybridSearch

    snippet_a = _Snippet("snippet-a")
    snippet_b = _Snippet("snippet-b")
    storage = MagicMock()
    storage.list_all.return_value = [snippet_a, snippet_b]

    with patch.object(HybridSearch, "__init__", lambda self, config: None):
        search = HybridSearch(None)
        search._config = MagicMock()
        search.vector_index = MagicMock()
        search.keyword_index = MagicMock()
        search.embedder = MagicMock()

    with (
        patch("snipcontext.core.storage.StorageEngine", return_value=storage),
        patch.object(search.vector_index, "save") as mock_save,
    ):
        search.add_snippet(snippet_b)

    search.vector_index.add_vector.assert_called_once_with(snippet_b, search.embedder)
    mock_save.assert_called_once_with(search._config.index_path)
    assert search._keyword_dirty is True


def test_remove_snippet_calls_vector_index_remove_vector() -> None:
    from snipcontext.core.search import HybridSearch

    snippet_a = _Snippet("snippet-a")
    snippet_b = _Snippet("snippet-b")
    storage = MagicMock()
    storage.list_all.return_value = [snippet_a, snippet_b]

    with patch.object(HybridSearch, "__init__", lambda self, config: None):
        search = HybridSearch(None)
        search._config = MagicMock()
        search.vector_index = MagicMock()
        search.keyword_index = MagicMock()

    with (
        patch("snipcontext.core.storage.StorageEngine", return_value=storage),
        patch.object(search.vector_index, "save") as mock_save,
    ):
        search.remove_snippet("snippet-a")

    search.vector_index.remove_vector.assert_called_once_with("snippet-a")
    mock_save.assert_called_once_with(search._config.index_path)
    assert search._keyword_dirty is True


def test_rebuild_incremental_excludes_soft_deleted() -> None:
    from snipcontext.core.search import HybridSearch

    snippet_a = _Snippet("snippet-a", deleted=False)
    snippet_b = _Snippet("snippet-b", deleted=True)

    with patch.object(HybridSearch, "__init__", lambda self, config: None):
        search = HybridSearch(None)
        search._config = MagicMock()

    with patch.object(search, "index_snippets") as mock_index:
        search.rebuild_incremental([snippet_a, snippet_b])

    called = mock_index.call_args[0][0]
    assert called == [snippet_a]


# ---------- StorageEngine.mark_deleted ----------


def test_mark_deleted_sets_flag_and_saves(tmp_path: Path) -> None:
    from snipcontext.core.storage import StorageEngine

    snippet_file = tmp_path / "snippet-a.json"
    snippet_file.write_text(
        '{"id":"snippet-a","content":"x","metadata":{"title":"test","language":"python","tags":[]}}',
        encoding="utf-8",
    )

    class _FakeConfig:
        def __init__(self, path):
            self.snippets_path = path
            self.index_path = path / "index"

        def ensure_directories(self):
            self.snippets_path.mkdir(parents=True, exist_ok=True)
            self.index_path.mkdir(parents=True, exist_ok=True)

    config = _FakeConfig(tmp_path)
    config.ensure_directories()

    engine = StorageEngine(config)
    # Override save to avoid depending on internal serialization details
    saved_calls = []
    engine.save = lambda snippet: saved_calls.append(snippet)

    engine.mark_deleted("snippet-a")

    assert "snippet-a" in engine._deleted_ids
    assert len(saved_calls) == 1
    assert saved_calls[0].deleted is True


# ---------- CLI index command ----------


def test_index_command_with_snippets() -> None:
    from snipcontext.cli.main import index

    snippet1 = _Snippet("snippet-1")
    snippet2 = _Snippet("snippet-2")

    with patch("snipcontext.cli.main.get_config") as mock_get_config:
        mock_config = MagicMock()
        mock_get_config.return_value = mock_config
        storage = MagicMock()
        storage.list_all.return_value = [snippet1, snippet2]
        with (
            patch("snipcontext.core.storage.StorageEngine", return_value=storage),
            patch("snipcontext.core.search.HybridSearch") as mock_search_cls,
            patch("snipcontext.cli.main.console"),
        ):
            mock_search = mock_search_cls.return_value
            index(force=False)

        mock_search.index_snippets.assert_called_once_with([snippet1, snippet2])


def test_index_command_empty_no_force_returns() -> None:
    from snipcontext.cli.main import index

    with patch("snipcontext.cli.main.get_config") as mock_get_config:
        mock_config = MagicMock()
        mock_get_config.return_value = mock_config
        storage = MagicMock()
        storage.list_all.return_value = []
        with (
            patch("snipcontext.core.storage.StorageEngine", return_value=storage),
            patch("snipcontext.cli.main.console") as mock_console,
            patch("snipcontext.core.search.HybridSearch") as mock_search_cls,
        ):
            index(force=False)

        mock_search_cls.return_value.index_snippets.assert_not_called()
        output = "".join(call.args[0] for call in mock_console.print.call_args_list)
        assert "No snippets found" in output


def test_index_command_empty_with_force() -> None:
    from snipcontext.cli.main import index

    with patch("snipcontext.cli.main.get_config") as mock_get_config:
        mock_config = MagicMock()
        mock_get_config.return_value = mock_config
        storage = MagicMock()
        storage.list_all.return_value = []
        with (
            patch("snipcontext.core.storage.StorageEngine", return_value=storage),
            patch("snipcontext.core.search.HybridSearch") as mock_search_cls,
            patch("snipcontext.cli.main.console"),
        ):
            index(force=True)

        mock_search_cls.return_value.index_snippets.assert_called_once_with([])
