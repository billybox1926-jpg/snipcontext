"""Tests for GitIntegration.conflict detection against real Snippet/StorageEngine."""

from __future__ import annotations

import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest

from snipcontext.config.settings import Config, StorageConfig, reset_config
from snipcontext.core.models import Snippet, SnippetMetadata
from snipcontext.core.storage import StorageEngine
from snipcontext.core.git_integration import GitIntegration


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _make_snippet(snippet_id: str, content: str, title: str) -> Snippet:
    return Snippet(
        id=snippet_id,
        content=content,
        metadata=SnippetMetadata(title=title, language="python"),
        tags=["python"],
        updated_at=_utc_now(),
    )


def _write_snippet(storage: StorageEngine, snippet: Snippet) -> None:
    storage.save(snippet)


def _init_git_repo(path: Path) -> None:
    subprocess.run(["git", "init", "-b", "main", str(path)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(path), "config", "user.email", "test@test.test"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(path), "config", "user.name", "Test"], check=True, capture_output=True)
    (path / ".gitignore").write_text("index.faiss\n")


def _make_bare_remote(tmp_path: Path, name: str = "remote.git") -> Path:
    remote = tmp_path / name
    subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(remote), "config", "user.email", "remote@test.test"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(remote), "config", "user.name", "Remote"], check=True, capture_output=True)
    return remote


def _commit_all(repo: Path, message: str) -> str:
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-m", message], check=True, capture_output=True)
    return subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _advance_time(seconds: float = 1.0) -> None:
    time.sleep(seconds)


class TestGitIntegrationConflictDetection:
    """End-to-end conflict detection against real Snippet/StorageEngine objects."""

    def test_real_conflict_flags_both_sides_edited(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        snippets_dir = repo / "snippets"
        snippets_dir.mkdir()

        config = Config(
            storage=StorageConfig(
                data_dir=repo,
                snippets_dir="snippets",
                index_dir="index",
            )
        )
        storage = StorageEngine(config)
        local = _make_snippet("s1", "print('local')", "Local Edit")
        remote_snippet = _make_snippet("s1", "print('remote')", "Remote Edit")
        _write_snippet(storage, local)

        remote = _make_bare_remote(tmp_path)
        _init_git_repo(repo)
        subprocess.run(["git", "-C", str(repo), "remote", "add", "origin", str(remote)], check=True, capture_output=True)

        base_sha = _commit_all(repo, "base: add s1")
        subprocess.run(["git", "-C", str(repo), "push", "origin", "main"], check=True, capture_output=True)

        # Simulate remote: change content and push
        _write_snippet(storage, remote_snippet)
        _commit_all(repo, "remote: edit s1")
        subprocess.run(["git", "-C", str(repo), "push", "origin", "main"], check=True, capture_output=True)

        # Reset to base, then simulate local: different change
        subprocess.run(["git", "-C", str(repo), "reset", "--hard", base_sha], check=True, capture_output=True)
        _write_snippet(storage, _make_snippet("s1", "print('local-v2')", "Local V2"))
        _commit_all(repo, "local: edit s1")

        git = GitIntegration(repo)
        report = git.detect_conflicts(storage, remote_name="origin")

        assert report.has_conflicts
        assert len(report.conflicts) == 1
        assert report.conflicts[0].snippet_id == "s1"

    def test_unrelated_snippet_change_is_not_conflict(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        snippets_dir = repo / "snippets"
        snippets_dir.mkdir()

        config = Config(
            storage=StorageConfig(
                data_dir=repo,
                snippets_dir="snippets",
                index_dir="index",
            )
        )
        storage = StorageEngine(config)
        local_s1 = _make_snippet("s1", "print('s1')", "S1")
        remote_s2 = _make_snippet("s2", "print('s2')", "S2")
        _write_snippet(storage, local_s1)

        remote = _make_bare_remote(tmp_path)
        _init_git_repo(repo)
        subprocess.run(["git", "-C", str(repo), "remote", "add", "origin", str(remote)], check=True, capture_output=True)

        base_sha = _commit_all(repo, "base")
        subprocess.run(["git", "-C", str(repo), "push", "origin", "main"], check=True, capture_output=True)

        subprocess.run(["git", "-C", str(repo), "reset", "--hard", base_sha], check=True, capture_output=True)
        _write_snippet(storage, _make_snippet("s1", "print('s1-v2')", "S1 V2"))
        _commit_all(repo, "local: edit s1")

        # Simulate remote changing only s2
        subprocess.run(["git", "-C", str(repo), "checkout", "-b", "remote"], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(repo), "reset", "--hard", base_sha], check=True, capture_output=True)
        _write_snippet(storage, remote_s2)
        _commit_all(repo, "remote: add s2")
        subprocess.run(["git", "-C", str(repo), "push", "--force", "origin", "remote:main"], check=True, capture_output=True)

        subprocess.run(["git", "-C", str(repo), "checkout", "main"], check=True, capture_output=True)

        git = GitIntegration(repo)
        report = git.detect_conflicts(storage, remote_name="origin")

        assert not report.has_conflicts

    def test_touch_only_without_content_change_is_not_conflict(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        snippets_dir = repo / "snippets"
        snippets_dir.mkdir()

        config = Config(
            storage=StorageConfig(
                data_dir=repo,
                snippets_dir="snippets",
                index_dir="index",
            )
        )
        storage = StorageEngine(config)
        local_s1 = _make_snippet("s1", "print('s1')", "S1")
        _write_snippet(storage, local_s1)

        remote = _make_bare_remote(tmp_path)
        _init_git_repo(repo)
        subprocess.run(["git", "-C", str(repo), "remote", "add", "origin", str(remote)], check=True, capture_output=True)

        base_sha = _commit_all(repo, "base")
        subprocess.run(["git", "-C", str(repo), "push", "origin", "main"], check=True, capture_output=True)

        subprocess.run(["git", "-C", str(repo), "reset", "--hard", base_sha], check=True, capture_output=True)
        _write_snippet(storage, local_s1)
        local_s1.touch()
        _write_snippet(storage, local_s1)
        _commit_all(repo, "local: touch s1")

        subprocess.run(["git", "-C", str(repo), "checkout", "-b", "remote"], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(repo), "reset", "--hard", base_sha], check=True, capture_output=True)
        _write_snippet(storage, local_s1)
        _commit_all(repo, "remote: touch s1")
        subprocess.run(["git", "-C", str(repo), "push", "--force", "origin", "remote:main"], check=True, capture_output=True)

        subprocess.run(["git", "-C", str(repo), "checkout", "main"], check=True, capture_output=True)

        git = GitIntegration(repo)
        report = git.detect_conflicts(storage, remote_name="origin")

        assert not report.has_conflicts

    def test_merge_base_failure_returns_empty_report(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        snippets_dir = repo / "snippets"
        snippets_dir.mkdir()

        config = Config(
            storage=StorageConfig(
                data_dir=repo,
                snippets_dir="snippets",
                index_dir="index",
            )
        )
        storage = StorageEngine(config)
        local = _make_snippet("s1", "print('local')", "Local")
        _write_snippet(storage, local)

        remote = _make_bare_remote(tmp_path)
        _init_git_repo(repo)
        subprocess.run(["git", "-C", str(repo), "remote", "add", "origin", str(remote)], check=True, capture_output=True)

        _commit_all(repo, "base")
        subprocess.run(["git", "-C", str(repo), "push", "origin", "main"], check=True, capture_output=True)

        # Create a second root commit unrelated to HEAD, push it as the remote ref.
        orphan = repo / "orphan.txt"
        orphan.write_text("orphan")
        subprocess.run(["git", "-C", str(repo), "add", "orphan.txt"], check=True, capture_output=True)
        subprocess.run(
            ["git", "-C", str(repo), "commit", "-m", "orphan", "--allow-empty"],
            check=True,
            capture_output=True,
        )
        orphan_sha = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        subprocess.run(["git", "-C", str(repo), "push", "--force", "origin", "HEAD:main"], check=True, capture_output=True)

        git = GitIntegration(repo)
        report = git.detect_conflicts(storage, remote_name="origin")

        assert not report.has_conflicts
        assert report.summary() == "No conflicting snippets found."
