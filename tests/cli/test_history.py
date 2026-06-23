"""Tests for search history CLI commands."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from snipcontext.cli.app import app
from snipcontext.core.search_history import SearchHistoryStore

runner = CliRunner()


@pytest.fixture()
def history_store(tmp_path: Path):
    """Isolated history store backed by a temp SQLite file."""
    db = tmp_path / "history.db"
    store = SearchHistoryStore(db_path=db)
    return store


def test_history_list_empty(tmp_path: Path, monkeypatch):
    """Sc history list shows empty state when no history exists."""
    from snipcontext.config.settings import reset_config

    monkeypatch.chdir(tmp_path)
    (tmp_path / ".snipcontext").mkdir()
    reset_config()

    with patch(
        "snipcontext.cli.history.SearchHistoryStore",
        return_value=SearchHistoryStore(db_path=tmp_path / "history.db"),
    ):
        result = runner.invoke(app, ["history", "list"])
    assert result.exit_code == 0
    assert "No search history yet" in result.output


def test_history_list_with_entries(tmp_path: Path, monkeypatch, history_store: SearchHistoryStore):
    """Sc history list shows recent entries."""
    from snipcontext.config.settings import reset_config

    monkeypatch.chdir(tmp_path)
    (tmp_path / ".snipcontext").mkdir()
    reset_config()

    history_store.add("auth flow", result_count=3)
    history_store.add("jwt decode", result_count=0)

    with patch("snipcontext.cli.history.SearchHistoryStore", return_value=history_store):
        result = runner.invoke(app, ["history", "list", "--limit", "5"])
    assert result.exit_code == 0
    assert "auth flow" in result.output
    assert "jwt decode" in result.output


def test_history_favorites_empty(tmp_path: Path, monkeypatch):
    """Sc history favorites shows empty state when no favorites exist."""
    from snipcontext.config.settings import reset_config

    monkeypatch.chdir(tmp_path)
    (tmp_path / ".snipcontext").mkdir()
    reset_config()

    with patch(
        "snipcontext.cli.history.SearchHistoryStore",
        return_value=SearchHistoryStore(db_path=tmp_path / "history.db"),
    ):
        result = runner.invoke(app, ["history", "favorites"])
    assert result.exit_code == 0
    assert "No favorites yet" in result.output


def test_history_favorites_with_entries(tmp_path: Path, history_store: SearchHistoryStore):
    """Sc history favorites shows favorited queries."""
    history_store.add("fastapi setup", result_count=5)
    eid = history_store.get_recent()[0].id
    history_store.toggle_favorite(eid)

    with patch("snipcontext.cli.history.SearchHistoryStore", return_value=history_store):
        result = runner.invoke(app, ["history", "favorites"])
    assert result.exit_code == 0
    assert "fastapi setup" in result.output


def test_history_add(tmp_path: Path, history_store: SearchHistoryStore):
    """Sc history add adds a query to history."""
    with patch("snipcontext.cli.history.SearchHistoryStore", return_value=history_store):
        result = runner.invoke(app, ["history", "add", "docker compose"])
    assert result.exit_code == 0
    assert "Added 'docker compose' to history" in result.output
    assert len(history_store.get_recent()) == 1


def test_history_add_with_favorite(tmp_path: Path, history_store: SearchHistoryStore):
    """Sc history add --favorite marks the new entry as favorite."""
    with patch("snipcontext.cli.history.SearchHistoryStore", return_value=history_store):
        result = runner.invoke(app, ["history", "add", "redis cache", "--favorite"])
    assert result.exit_code == 0
    entries = history_store.get_recent()
    assert len(entries) == 1
    assert entries[0].is_favorite is True


def test_history_favorite_toggle(tmp_path: Path, history_store: SearchHistoryStore):
    """Sc history favorite <id> toggles favorite status."""
    history_store.add("sqlite pool", result_count=2)
    eid = history_store.get_recent()[0].id

    with patch("snipcontext.cli.history.SearchHistoryStore", return_value=history_store):
        result = runner.invoke(app, ["history", "favorite", str(eid)])
    assert result.exit_code == 0
    assert "favorited" in result.output
    assert history_store.get_by_id(eid).is_favorite is True

    with patch("snipcontext.cli.history.SearchHistoryStore", return_value=history_store):
        result = runner.invoke(app, ["history", "favorite", str(eid)])
    assert result.exit_code == 0
    assert "unfavorited" in result.output


def test_history_favorite_missing_id(tmp_path: Path, history_store: SearchHistoryStore):
    """Sc history favorite <missing-id> reports error."""
    with patch("snipcontext.cli.history.SearchHistoryStore", return_value=history_store):
        result = runner.invoke(app, ["history", "favorite", "9999"])
    assert result.exit_code == 1
    assert "No history entry with ID 9999" in result.output


def test_history_clear_with_force(tmp_path: Path, history_store: SearchHistoryStore):
    """Sc history clear --force clears all history without prompt."""
    history_store.add("cleanup test", result_count=1)

    with patch("snipcontext.cli.history.SearchHistoryStore", return_value=history_store):
        result = runner.invoke(app, ["history", "clear", "--force"])
    assert result.exit_code == 0
    assert "Search history cleared" in result.output
    assert len(history_store.get_recent()) == 0
