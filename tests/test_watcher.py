"""Tests for the watchdog watcher integration."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from snipcontext.core.watcher import SnippetChangeHandler, SnippetWatcher


class _Search:
    def __init__(self) -> None:
        self.rebuild_called = False
        self.last_snippets = []

    def rebuild_incremental(self, snippets) -> None:
        self.rebuild_called = True
        self.last_snippets = list(snippets)


class _Storage:
    def list_all(self):
        return []


class _Config:
    def __init__(self, snippets_path: Path, watchdog_enabled: bool = True) -> None:
        self.snippets_path = snippets_path
        self.watchdog_enabled = watchdog_enabled


def test_watcher_event_triggers_incremental_rebuild() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        snippets_dir = Path(tmpdir)
        snippet_file = snippets_dir / "abc123.json"
        snippet_file.write_text("{}", encoding="utf-8")

        search = _Search()
        storage = _Storage()
        handler = SnippetChangeHandler(search, storage)

        try:
            from watchdog.events import FileCreatedEvent
            event = FileCreatedEvent(str(snippet_file))
        except ImportError as exc:
            pytest.skip(f"watchdog not available: {exc}")

        handler.on_any_event(event)

        assert search.rebuild_called is True


def test_watcher_disabled_config_does_nothing() -> None:
    watcher = SnippetWatcher(_Config(Path("."), watchdog_enabled=False), _Search(), _Storage())
    watcher.start()
    assert not hasattr(watcher, "observer") or getattr(watcher, "observer", None) is None


def test_watcher_missing_watchdog_graceful() -> None:
    import snipcontext.core.watcher as watcher_module

    original = watcher_module._WATCHDOG_AVAILABLE
    try:
        watcher_module._WATCHDOG_AVAILABLE = False
        watcher = SnippetWatcher(_Config(Path(".")), _Search(), _Storage())
        watcher.start()
        assert not hasattr(watcher, "observer") or getattr(watcher, "observer", None) is None
    finally:
        watcher_module._WATCHDOG_AVAILABLE = original


def test_watcher_keyboard_interrupt_stops_observer() -> None:
    config = _Config(Path("."))
    watcher = SnippetWatcher(config, _Search(), _Storage())

    observer = MagicMock()
    observer.join.side_effect = [KeyboardInterrupt, None]
    observer.is_alive.return_value = True
    watcher.observer = observer

    with patch("snipcontext.core.watcher.Observer", return_value=observer):
        watcher.start()

    observer.stop.assert_called_once()
    assert observer.join.call_count == 2