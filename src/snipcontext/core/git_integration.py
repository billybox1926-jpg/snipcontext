"""Git integration for SnipContext.

Implements the mechanics behind `sc init --git` and `sc git status/push/pull`
(issue #37): repo init, a sensible .gitignore, an initial commit, optional
remote setup, and conflict detection before pull/rebase.

Design notes
------------
- Uses subprocess + the system `git` binary rather than GitPython. The
  surface area needed here (init, add, commit, remote, fetch, show, diff) is
  small and easy to shell out to; it avoids adding a dependency with its own
  release cadence for a feature most users will touch occasionally.
- Conflict detection compares snippet IDs + `updated_at` timestamps, per the
  issue's suggested approach, rather than doing a real git merge/diff on the
  JSON files themselves. This lets SnipContext warn *before* invoking git's
  own merge machinery, at the snippet-record level instead of the line level.

Field names below are confirmed against the actual codebase:
  - Snippet.id            — uuid4()-derived stem, stable, never changes
  - Snippet.content_hash  — sha256(content.encode()).hexdigest()[:16]
  - Snippet.updated_at    — datetime, bumped by Snippet.touch()
  - Snippet.deleted       — soft-delete flag, persisted
  - Snippet.embedding     — NOT persisted (vector index only) — irrelevant here
  - StorageEngine.list_all() -> list[Snippet]
  - StorageEngine.save(snippet) -> Path, writes `{id}.json`, excludes embedding

One deliberate deviation from the issue's suggested approach: conflict
detection below treats `content_hash` (+ `deleted`) as the source of truth
for "did this snippet actually change", and only uses `updated_at` for the
human-readable report. Using timestamps alone would produce false positives
from a bare `touch()` with no content change, and is vulnerable to clock
skew between machines; comparing hashes against the merge-base is exact.

Ancestor/remote state is read by materializing each ref into a throwaway
`git worktree`, per the issue's suggestion of "checking out the merge-base
commit's snippets directory temporarily" — this reads all snippet files in
one shot rather than one `git show <ref>:<path>` call per file.

Assumption still open: the on-disk snippet JSON is assumed to live either
directly under `storage_dir` or under a `snippets/` subdirectory (matching
the `.snipcontext/snippets/` layout shown in the README's project-local
mode). Adjust `_SNIPPETS_SUBDIR` if the global (non-project-local) layout
differs.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional

_SNIPPETS_SUBDIR = "snippets"


DEFAULT_GITIGNORE = """\
# Managed by SnipContext (sc init --git)
index.faiss
index.faiss.meta
*.tmp
.env
"""


class GitError(RuntimeError):
    """Raised for any git-related failure that should surface to the CLI."""


@dataclass
class ConflictEntry:
    snippet_id: str
    local_updated_at: Optional[datetime]
    remote_updated_at: Optional[datetime]


@dataclass
class ConflictReport:
    conflicts: list[ConflictEntry] = field(default_factory=list)

    @property
    def has_conflicts(self) -> bool:
        return bool(self.conflicts)

    def summary(self) -> str:
        if not self.conflicts:
            return "No conflicting snippets found."
        lines = [f"{len(self.conflicts)} snippet(s) changed on both sides:"]
        for c in self.conflicts:
            lines.append(
                f"  - {c.snippet_id}: local updated {c.local_updated_at}, "
                f"remote updated {c.remote_updated_at}"
            )
        return "\n".join(lines)


class GitIntegration:
    """Wraps git operations for a SnipContext storage directory."""

    def __init__(self, storage_dir: Path):
        self.storage_dir = Path(storage_dir)

    # ---------------------------------------------------------- setup --

    def is_initialized(self) -> bool:
        return (self.storage_dir / ".git").exists()

    def init_repo(self) -> None:
        if self.is_initialized():
            raise GitError(f"{self.storage_dir} is already a git repository.")
        if shutil.which("git") is None:
            raise GitError("git is not installed or not on PATH.")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._run("init")

    def write_gitignore(self, extra_patterns: Optional[Iterable[str]] = None) -> Path:
        """Create .gitignore, excluding the search index, temp files, and .env.

        Merges with an existing .gitignore if one is already present, rather
        than overwriting it, so re-running `sc init --git` is idempotent.
        """
        path = self.storage_dir / ".gitignore"
        existing = path.read_text(encoding="utf-8") if path.exists() else ""
        existing_lines = {ln.strip() for ln in existing.splitlines() if ln.strip()}

        default_lines = [
            ln for ln in DEFAULT_GITIGNORE.splitlines() if ln.strip() and not ln.startswith("#")
        ]
        to_add = [ln for ln in default_lines if ln not in existing_lines]
        if extra_patterns:
            to_add += [p for p in extra_patterns if p not in existing_lines]

        if not existing:
            path.write_text(DEFAULT_GITIGNORE, encoding="utf-8")
            if extra_patterns:
                with path.open("a", encoding="utf-8") as f:
                    f.write("\n# Project-specific\n" + "\n".join(extra_patterns) + "\n")
        elif to_add:
            with path.open("a", encoding="utf-8") as f:
                f.write("\n# Added by sc init --git\n" + "\n".join(to_add) + "\n")

        return path

    def initial_commit(self, message: str = "Initial snippet collection") -> Optional[str]:
        """Stage everything and commit. Returns the new commit SHA, or None
        if there was nothing to commit (e.g. an empty collection)."""
        self._run("add", "-A")
        status = self._run("status", "--porcelain")
        if not status.strip():
            return None
        self._run("commit", "-m", message)
        return self._run("rev-parse", "HEAD").strip()

    def add_remote(self, url: str, name: str = "origin") -> None:
        existing = self._run("remote").split()
        if name in existing:
            self._run("remote", "set-url", name, url)
        else:
            self._run("remote", "add", name, url)

    # --------------------------------------------------------- status --

    def status(self) -> str:
        return self._run("status", "--short", "--branch")

    def current_branch(self) -> str:
        return self._run("rev-parse", "--abbrev-ref", "HEAD").strip()

    # ------------------------------------------------- conflict checks --

    def detect_conflicts(self, storage, remote_name: str = "origin") -> ConflictReport:
        """Compare local snippet state against the fetched remote-tracking ref.

        Intended to run before `sc git pull` / `sc git rebase`. Fetches
        first so the check is against the latest known remote state, then
        classifies each snippet present on both sides as a real conflict
        only if its `content_hash` (or `deleted` flag) differs from the
        merge-base on *both* the local and remote side. A snippet that only
        changed on one side is a fast-forward, not a conflict.
        """
        try:
            self._run("fetch", remote_name, "--quiet")
        except GitError:
            # No remote, or offline — nothing to compare against.
            return ConflictReport()

        remote_ref = self._remote_tracking_ref(remote_name)
        if remote_ref is None:
            return ConflictReport()

        try:
            merge_base = self._run("merge-base", "HEAD", remote_ref).strip()
        except GitError:
            # Unrelated histories, or no common ancestor — nothing sane to
            # diff against; let `git pull` surface its own error instead.
            return ConflictReport()

        remote_snippets = self._read_ref_snippets(remote_ref)
        base_snippets = self._read_ref_snippets(merge_base)
        local_snippets = self._read_local_snippets(storage)

        conflicts: list[ConflictEntry] = []
        for snippet_id in set(local_snippets) | set(remote_snippets):
            local = local_snippets.get(snippet_id)
            remote = remote_snippets.get(snippet_id)
            if local is None or remote is None:
                continue  # added/deleted on only one side — not a same-snippet conflict

            if local["content_hash"] == remote["content_hash"] and local["deleted"] == remote["deleted"]:
                continue  # both sides ended up in the same state — nothing to warn about

            base = base_snippets.get(snippet_id)
            local_changed = base is None or (
                local["content_hash"] != base["content_hash"] or local["deleted"] != base["deleted"]
            )
            remote_changed = base is None or (
                remote["content_hash"] != base["content_hash"] or remote["deleted"] != base["deleted"]
            )

            if local_changed and remote_changed:
                conflicts.append(
                    ConflictEntry(
                        snippet_id=snippet_id,
                        local_updated_at=local["updated_at"],
                        remote_updated_at=remote["updated_at"],
                    )
                )

        return ConflictReport(conflicts)

    # ------------------------------------------------------- internals --

    def _read_local_snippets(self, storage) -> dict[str, dict]:
        result = {}
        for snippet in storage.list_all():
            result[snippet.id] = {
                "content_hash": snippet.content_hash,
                "deleted": snippet.deleted,
                "updated_at": snippet.updated_at,
            }
        return result

    def _remote_tracking_ref(self, remote_name: str = "origin") -> Optional[str]:
        try:
            branch = self.current_branch()
            ref = f"{remote_name}/{branch}"
            self._run("rev-parse", "--verify", ref)
            return ref
        except GitError:
            return None

    def _read_ref_snippets(self, ref: str) -> dict[str, dict]:
        """Materialize `ref` into a throwaway worktree and read every
        snippet JSON file, returning id -> {content_hash, deleted, updated_at}.

        `content_hash` is recomputed from `content` here rather than trusted
        from disk, since it's a derived field and this keeps detection
        correct even if a stored value were ever stale.
        """
        tmp = Path(tempfile.mkdtemp(prefix="sc-conflict-"))
        # git worktree add requires the target to not already exist as a
        # non-empty dir; mkdtemp's empty dir is fine, but remove it so `add`
        # can create it fresh and avoid any platform quirks with existing dirs.
        tmp.rmdir()
        result: dict[str, dict] = {}
        try:
            self._run("worktree", "add", "--detach", str(tmp), ref)
            snippet_dir = tmp / _SNIPPETS_SUBDIR
            if not snippet_dir.is_dir():
                snippet_dir = tmp
            for path in snippet_dir.glob("*.json"):
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    continue
                snippet_id = data.get("id", path.stem)
                content = data.get("content", "")
                updated_at_raw = data.get("updated_at")
                try:
                    updated_at = (
                        datetime.fromisoformat(updated_at_raw) if updated_at_raw else None
                    )
                except ValueError:
                    updated_at = None
                result[snippet_id] = {
                    "content_hash": hashlib.sha256(content.encode()).hexdigest()[:16],
                    "deleted": bool(data.get("deleted", False)),
                    "updated_at": updated_at,
                }
        except GitError:
            return {}
        finally:
            try:
                self._run("worktree", "remove", "--force", str(tmp))
            except GitError:
                pass
            shutil.rmtree(tmp, ignore_errors=True)
        return result

    def _run(self, *args: str) -> str:
        try:
            proc = subprocess.run(
                ["git", "-C", str(self.storage_dir), *args],
                capture_output=True,
                text=True,
                check=True,
            )
        except FileNotFoundError as exc:
            raise GitError("git is not installed or not on PATH.") from exc
        except subprocess.CalledProcessError as exc:
            raise GitError(
                f"git {' '.join(args)} failed: {exc.stderr.strip() or exc.stdout.strip()}"
            ) from exc
        return proc.stdout
