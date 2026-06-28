"""Git-friendly local storage engine for SnipContext.

Each snippet is stored as an individual JSON file organized in a
directory tree by tags. This design ensures:
- Human-readable, diff-friendly storage
- Git version control works naturally
- No lock files or binary databases
- Easy to inspect and modify manually
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator

from snipcontext.config.settings import Config, get_config
from snipcontext.core.models import Snippet

logger = logging.getLogger(__name__)


class StorageError(Exception):
    """Base exception for storage operations."""


class SnippetNotFoundError(StorageError):
    """Raised when a requested snippet does not exist."""


class IndexCorruptedError(StorageError):
    """Raised when a search index is detected as corrupted or invalid."""

    def __init__(self, index_type: str, path: str, original_error: Exception | None = None):
        self.index_type = index_type
        self.path = path
        self.original_error = original_error
        msg = f"Index corrupted: {index_type} at {path}"
        if original_error:
            msg += f" (caused by: {original_error})"
        super().__init__(msg)


class MissingIndexError(StorageError):
    """Raised when a required search index is missing."""

    def __init__(self, index_type: str, path: str):
        self.index_type = index_type
        self.path = path
        super().__init__(f"Index missing: {index_type} at {path}")


class StorageEngine:
    """Manages persistent storage of snippets on the local filesystem.

    Uses a directory-based layout optimized for git tracking:
        ~/.local/share/SnipContext/
        ├── snippets/
        │   ├── abc123.json
        │   └── def456.json
        └── index/
            ├── vector.faiss
            └── metadata.json

    Each snippet is a self-contained JSON file with a deterministic filename
    based on the snippet ID. This makes diffs, merges, and manual inspection
    straightforward.
    """

    def __init__(self, config: Config | None = None) -> None:
        self._config = config or get_config()
        self._config.ensure_directories()
        self._deleted_ids: set[str] = set()

    @property
    def snippets_dir(self) -> Path:
        return self._config.snippets_path

    @property
    def index_dir(self) -> Path:
        return self._config.index_path

    @property
    def deleted_ids(self) -> set[str]:
        return set(self._deleted_ids)

    def mark_deleted(self, snippet_id: str) -> None:
        """Mark a snippet as soft-deleted and persist the change."""
        self._deleted_ids.add(snippet_id)
        snippet = self.get(snippet_id)
        if snippet is not None:
            snippet.deleted = True
            self.save(snippet)

    def _snippet_path(self, snippet_id: str) -> Path:
        """Compute the filesystem path for a snippet by ID."""
        return self.snippets_dir / f"{snippet_id}.json"

    # ------------------------------------------------------------------
    # CRUD operations
    # ------------------------------------------------------------------

    def save(self, snippet: Snippet) -> Path:
        """Persist a snippet to disk.

        Args:
            snippet: The snippet to save. Will be serialized to JSON.

        Returns:
            Path to the saved file.

        Raises:
            StorageError: If the snippet cannot be written.
        """
        path = self._snippet_path(snippet.id)
        data = snippet.model_dump(mode="json")

        # Remove embedding from JSON - it's stored in the vector index
        data.pop("embedding", None)

        try:
            with open(path, "w", encoding="utf-8") as f:
                if self._config.storage.pretty_json:
                    json.dump(data, f, indent=self._config.storage.json_indent, ensure_ascii=False)
                else:
                    json.dump(data, f, ensure_ascii=False)
                f.write("\n")
        except (OSError, TypeError) as exc:
            raise StorageError(f"Failed to save snippet {snippet.id}: {exc}") from exc

        logger.debug("Saved snippet %s to %s", snippet.id, path)
        return path

    def get(self, snippet_id: str) -> Snippet:
        """Load a snippet from disk by ID.

        Args:
            snippet_id: The unique snippet identifier.

        Returns:
            The deserialized Snippet object.

        Raises:
            SnippetNotFoundError: If the snippet file does not exist.
            StorageError: If the file cannot be read or parsed.
        """
        path = self._snippet_path(snippet_id)
        if not path.exists():
            raise SnippetNotFoundError(f"Snippet not found: {snippet_id}")

        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError) as exc:
            raise StorageError(f"Failed to load snippet {snippet_id}: {exc}") from exc

        return Snippet.model_validate(data)

    def delete(self, snippet_id: str) -> bool:
        """Delete a snippet from disk.

        Args:
            snippet_id: The unique snippet identifier.

        Returns:
            True if deleted, False if it didn't exist.
        """
        path = self._snippet_path(snippet_id)
        if path.exists():
            path.unlink()
            logger.debug("Deleted snippet %s", snippet_id)
            return True
        return False

    def exists(self, snippet_id: str) -> bool:
        """Check if a snippet exists on disk."""
        return self._snippet_path(snippet_id).exists()

    def find_by_content_hash(self, content_hash: str) -> Snippet | None:
        """Find a snippet by exact content hash.

        Args:
            content_hash: SHA-256 prefix to match.

        Returns:
            The first matching snippet, or None.
        """
        for snippet in self.iter_all():
            if snippet.content_hash == content_hash:
                return snippet
        return None

    # ------------------------------------------------------------------
    # Bulk operations
    # ------------------------------------------------------------------

    def iter_all(self) -> Iterator[Snippet]:
        """Iterate over all stored snippets.

        Yields:
            Snippet objects in filesystem order.

        Raises:
            StorageError: If a file cannot be loaded (logged, not raised per-item).
        """
        if not self.snippets_dir.exists():
            return

        for path in sorted(self.snippets_dir.glob("*.json")):
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                yield Snippet.model_validate(data)
            except Exception:
                logger.warning("Skipping unreadable snippet file: %s", path)
                continue

    def list_all(self) -> list[Snippet]:
        """Load all snippets into a list."""
        return list(self.iter_all())

    def count(self) -> int:
        """Return the total number of stored snippets."""
        return sum(1 for _ in self.snippets_dir.glob("*.json") if _.is_file())

    # ------------------------------------------------------------------
    # Tag-based organization helpers
    # ------------------------------------------------------------------

    def find_by_tag(self, tag: str) -> list[Snippet]:
        """Find snippets containing a specific tag.

        This is a simple scan; for production queries, use the search index.
        """
        tag = tag.strip().lower()
        return [s for s in self.iter_all() if tag in s.tags]

    def get_tags(self, snippet_id: str) -> tuple[str, ...]:
        """Return normalized tags for a single stored snippet, or an empty tuple if missing."""
        try:
            return tuple(self.get(snippet_id).tags)
        except StorageError:
            return tuple()

    def get_all_tags(self) -> list[str]:
        """Return a sorted list of all unique tags across all snippets."""
        tags: set[str] = set()
        for snippet in self.iter_all():
            tags.update(snippet.tags)
        return sorted(tags)

    def get_stats(self) -> dict:
        """Return statistics about the snippet collection."""
        snippets = self.list_all()
        if not snippets:
            return {
                "total_snippets": 0,
                "total_tags": 0,
                "languages": {},
                "tags": {},
                "oldest": None,
                "newest": None,
                "deleted_count": 0,
                "total_size_bytes": 0,
            }

        from collections import Counter

        languages: Counter = Counter(s.metadata.language.value for s in snippets)
        tags: Counter = Counter()
        total_size = 0
        deleted_count = 0

        for s in snippets:
            for tag in s.tags:
                tags[tag] += 1
            total_size += len(s.content.encode("utf-8"))
            if s.deleted:
                deleted_count += 1

        return {
            "total_snippets": len(snippets),
            "total_tags": len(tags),
            "languages": dict(languages.most_common()),
            "tags": dict(tags.most_common()),
            "oldest": min(s.created_at for s in snippets).isoformat(),
            "newest": max(s.updated_at for s in snippets).isoformat(),
            "deleted_count": deleted_count,
            "total_size_bytes": total_size,
        }

    # ------------------------------------------------------------------
    # Maintenance
    # ------------------------------------------------------------------

    def reindex_all(self) -> int:
        """Rewrite all snippet files (useful after schema migrations).

        Returns:
            Number of snippets reindexed.
        """
        count = 0
        for snippet in self.iter_all():
            self.save(snippet)
            count += 1
        logger.info("Reindexed %d snippets", count)
        return count

    def vacuum(self) -> int:
        """Remove orphaned files and compress storage.

        Only removes files whose stem is not a valid snippet ID that can
        be loaded.

        Returns:
            Number of bytes freed.
        """
        freed = 0
        valid_ids: set[str] = set()

        for path in self.snippets_dir.glob("*.json"):
            snippet_id = path.stem
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                Snippet.model_validate(data)
                valid_ids.add(snippet_id)
            except Exception:
                pass

        for path in self.snippets_dir.glob("*.json"):
            snippet_id = path.stem
            if snippet_id not in valid_ids:
                freed += path.stat().st_size
                path.unlink()
                logger.debug("Vacuumed orphaned file: %s", path.name)

        return freed

    def export_all(self, output_path: Path) -> Path:
        """Export all snippets to a single JSON file.

        Args:
            output_path: Destination file path.

        Returns:
            Path to the exported file.
        """
        snippets = [s.model_dump(mode="json") for s in self.iter_all()]
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump({"snippets": snippets, "count": len(snippets)}, f, indent=2)
        logger.info("Exported %d snippets to %s", len(snippets), output_path)
        return output_path

    def import_file(self, input_path: Path) -> int:
        """Import snippets from a JSON export file.

        Args:
            input_path: Path to the JSON export file.

        Returns:
            Number of snippets imported.

        Raises:
            StorageError: If the file cannot be read.
        """
        input_path = Path(input_path)
        try:
            with open(input_path, encoding="utf-8") as f:
                payload = json.load(f)
        except (OSError, json.JSONDecodeError) as exc:
            raise StorageError(f"Failed to read import file {input_path}: {exc}") from exc

        items = payload.get("snippets") if isinstance(payload, dict) else None
        if items is None and isinstance(payload, list):
            items = payload
        elif items is None:
            items = payload.get("data", []) if isinstance(payload, dict) else []
        if not isinstance(items, list):
            items = [items]

        count = 0
        for item in items:
            try:
                snippet = Snippet.model_validate(item)
                self.save(snippet)
                count += 1
            except Exception as exc:
                logger.warning("Skipping invalid import item: %s", exc)
                continue

        logger.info("Imported %d snippets from %s", count, input_path)
        return count
