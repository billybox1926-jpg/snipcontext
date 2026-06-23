"""Tests for search history and favorites."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from typer.testing import CliRunner
from unittest.mock import patch

from snipcontext.cli.app import app
from snipcontext.cli.search import _get_history
from snipcontext.core.search_history import SearchHistoryStore

runner = CliRunner()


@pytest.fixture()
def history_store(tmp_path: Path, monkeypatch):
    """Isolated history store backed by a temp SQLite file."""
    db = tmp_path / "history.db"
    store = SearchHistoryStore(db_path=db)
    return store


def test_add_and_get_recent(history_store: SearchHistoryStore):
    history_store.add("auth flow", result_count=3)
    history_store.add("jwt decode", result_count=0)
    entries = history_store.get_recent(limit=10)
    assert len(entries) == 2
    assert entries[0].query == "jwt decode"
    assert entries[0].result_count == 0
    assert entries[1].query == "auth flow"
    assert entries[1].result_count == 3


def test_get_favorites(history_store: SearchHistoryStore):
    history_store.add("fastapi setup", result_count=5)
    eid = history_store.get_recent()[0].id
    history_store.toggle_favorite(eid)
    history_store.add("sqlite pool", result_count=2)

    favs = history_store.get_favorites()
    assert len(favs) == 1
    assert favs[0].query == "fastapi setup"
    assert favs[0].is_favorite is True

    all_recent = history_store.get_recent()
    # Most recent first: sqlite pool (id=2, not fav), fastapi setup (id=1, fav)
    assert all_recent[0].query == "sqlite pool"
    assert all_recent[0].is_favorite is False
    assert all_recent[1].query == "fastapi setup"
    assert all_recent[1].is_favorite is True


def test_toggle_favorite(history_store: SearchHistoryStore):
    history_store.add("redis cache", result_count=1)
    eid = history_store.get_recent()[0].id
    assert history_store.get_by_id(eid).is_favorite is False
    assert history_store.toggle_favorite(eid) is True
    assert history_store.get_by_id(eid).is_favorite is True
    assert history_store.toggle_favorite(eid) is False
    assert history_store.get_by_id(eid).is_favorite is False


def test_toggle_favorite_missing_id(history_store: SearchHistoryStore):
    assert history_store.toggle_favorite(9999) is False


def test_clear_history(history_store: SearchHistoryStore):
    history_store.add("query one", result_count=1)
    history_store.add("query two", result_count=2)
    assert len(history_store.get_recent()) == 2
    history_store.clear()
    assert len(history_store.get_recent()) == 0


def test_prune_older_than(history_store: SearchHistoryStore):
    from datetime import datetime, timedelta

    old_ts = (datetime.now() - timedelta(days=10)).isoformat()
    very_old_ts = (datetime.now() - timedelta(days=100)).isoformat()

    with history_store._connect() as conn:
        conn.execute(
            "INSERT INTO search_history (query, timestamp) VALUES (?, ?)",
            ("old query", old_ts),
        )
        conn.execute(
            "INSERT INTO search_history (query, timestamp) VALUES (?, ?)",
            ("ancient query", very_old_ts),
        )
        conn.commit()

    deleted = history_store.prune_older_than(days=30)
    assert deleted == 1
    remaining = [e.query for e in history_store.get_recent(limit=100)]
    assert "old query" in remaining
    assert "ancient query" not in remaining


def test_cli_search_history_option(tmp_path: Path, monkeypatch):
    """sc search --history displays history table."""
    from snipcontext.config.paths import get_storage_root
    from snipcontext.config.settings import get_config, reset_config

    monkeypatch.chdir(tmp_path)
    (tmp_path / ".snipcontext").mkdir()
    reset_config()

    result = runner.invoke(app, ["search", "--history"])
    assert result.exit_code == 0
    assert "No search history yet" in result.output


def test_cli_search_favorites_option(tmp_path: Path, monkeypatch):
    result = runner.invoke(app, ["search", "--favorites"])
    assert result.exit_code == 0
    assert "No favorites yet" in result.output


def test_cli_search_favorite_toggle(tmp_path: Path, history_store: SearchHistoryStore):
    history_store.add("docker compose", result_count=4)
    eid = history_store.get_recent()[0].id
    with patch("snipcontext.cli.search._get_history", return_value=history_store):
        result = runner.invoke(app, ["search", "--favorite", str(eid)])
    assert result.exit_code == 0, result.output
    assert "favorited" in result.output


def test_cli_search_clear_history(tmp_path: Path, monkeypatch, history_store: SearchHistoryStore):
    history_store.add("cleanup test", result_count=1)
    with patch.object(_get_history, "__call__", return_value=history_store):
        result = runner.invoke(app, ["search", "--clear-history"])
    assert result.exit_code == 0, result.output
    assert "Search history cleared" in result.output
