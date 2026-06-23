"""Search history and favorites store (SQLite)."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable


@dataclass
class SearchHistoryEntry:
    id: int
    query: str
    timestamp: datetime
    result_count: int
    is_favorite: bool


class SearchHistoryStore:
    """Persistent search history backed by SQLite."""

    def __init__(self, db_path: Path | None = None):
        if db_path is None:
            from snipcontext.config.paths import get_storage_root

            root = get_storage_root()
            root.mkdir(parents=True, exist_ok=True)
            self.db_path = root / "search_history.db"
        else:
            self.db_path = db_path
        self._ensure_tables()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_tables(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS search_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    result_count INTEGER DEFAULT 0,
                    is_favorite BOOLEAN DEFAULT 0
                )
                """
            )
            conn.commit()

    def add(self, query: str, result_count: int = 0) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                "INSERT INTO search_history (query, result_count) VALUES (?, ?)",
                (query, result_count),
            )
            conn.commit()
            return cursor.lastrowid

    def get_recent(self, limit: int = 50) -> list[SearchHistoryEntry]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, query, timestamp, result_count, is_favorite "
                "FROM search_history ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [self._row_to_entry(row) for row in rows]

    def get_favorites(self, limit: int = 100) -> list[SearchHistoryEntry]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, query, timestamp, result_count, is_favorite "
                "FROM search_history WHERE is_favorite = 1 ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [self._row_to_entry(row) for row in rows]

    def toggle_favorite(self, entry_id: int) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT is_favorite FROM search_history WHERE id = ?",
                (entry_id,),
            ).fetchone()
            if not row:
                return False
            new_val = 0 if row["is_favorite"] else 1
            conn.execute(
                "UPDATE search_history SET is_favorite = ? WHERE id = ?",
                (new_val, entry_id),
            )
            conn.commit()
            return bool(new_val)

    def get_by_id(self, entry_id: int) -> SearchHistoryEntry | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, query, timestamp, result_count, is_favorite "
                "FROM search_history WHERE id = ?",
                (entry_id,),
            ).fetchone()
        if row:
            return self._row_to_entry(row)
        return None

    def clear(self) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM search_history")
            conn.commit()

    def prune_older_than(self, days: int) -> int:
        cutoff = datetime.now() - timedelta(days=days)
        with self._connect() as conn:
            cursor = conn.execute(
                "DELETE FROM search_history WHERE timestamp < ?",
                (cutoff.isoformat(),),
            )
            conn.commit()
            return cursor.rowcount

    def _row_to_entry(self, row: sqlite3.Row) -> SearchHistoryEntry:
        return SearchHistoryEntry(
            id=row["id"],
            query=row["query"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            result_count=row["result_count"],
            is_favorite=bool(row["is_favorite"]),
        )
