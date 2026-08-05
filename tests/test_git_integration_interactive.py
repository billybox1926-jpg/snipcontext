import json
import os
import subprocess
from collections.abc import Generator
from pathlib import Path

import pytest
from typer.testing import CliRunner

from snipcontext.cli.app import app
from snipcontext.cli.context import reset_context

runner = CliRunner()
_NOW_COUNTER = 0


def _now_iso() -> str:
    global _NOW_COUNTER
    _NOW_COUNTER += 1
    return f"2026-08-05T03:{_NOW_COUNTER:02d}:00.000000+00:00"


@pytest.fixture(autouse=True)
def _reset_time_counter() -> Generator[None, None, None]:
    global _NOW_COUNTER
    _NOW_COUNTER = 0
    yield
    _NOW_COUNTER = 0


class TestGitCliInteractive:
    """CLI tests for the interactive conflict resolution flow."""

    def _setup_conflict_repo(self, tmp_path: Path) -> Path:
        """Helper: set up a repo with a conflicting local/remote pair."""
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / ".snipcontext").mkdir()
        (repo / ".snipcontext" / "snippets").mkdir()
        (repo / ".snipcontext" / "config.yaml").write_text(
            "storage:\n  data_dir: .snipcontext\n  snippets_dir: snippets\n  index_dir: index\n",
            encoding="utf-8",
        )
        os.chdir(repo)

        remote = tmp_path / "remote.git"
        subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
        subprocess.run(
            ["git", "init", "-b", "main", str(repo / ".snipcontext")],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(repo / ".snipcontext"), "config", "user.email", "local@test.test"],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(repo / ".snipcontext"), "config", "user.name", "Local"],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(repo / ".snipcontext"), "remote", "add", "origin", str(remote)],
            check=True,
            capture_output=True,
        )
        (repo / ".snipcontext" / "snippets" / "s1.json").write_text(
            json.dumps(
                {
                    "id": "s1",
                    "content": "print('base')",
                    "tags": [],
                    "updated_at": _now_iso(),
                    "deleted": False,
                }
            ),
            encoding="utf-8",
        )
        subprocess.run(
            ["git", "-C", str(repo / ".snipcontext"), "add", "-A"], check=True, capture_output=True
        )
        subprocess.run(
            ["git", "-C", str(repo / ".snipcontext"), "commit", "-m", "base"],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(repo / ".snipcontext"), "push", "origin", "main"],
            check=True,
            capture_output=True,
        )

        # Remote edits s1 and pushes.
        subprocess.run(
            ["git", "-C", str(repo / ".snipcontext"), "checkout", "-b", "remote"],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(repo / ".snipcontext"), "reset", "--hard", "main"],
            check=True,
            capture_output=True,
        )
        (repo / ".snipcontext" / "snippets" / "s1.json").write_text(
            json.dumps(
                {
                    "id": "s1",
                    "content": "print('remote')",
                    "tags": [],
                    "updated_at": _now_iso(),
                    "deleted": False,
                }
            ),
            encoding="utf-8",
        )
        subprocess.run(
            ["git", "-C", str(repo / ".snipcontext"), "add", "-A"], check=True, capture_output=True
        )
        subprocess.run(
            ["git", "-C", str(repo / ".snipcontext"), "commit", "-m", "remote: edit s1"],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(repo / ".snipcontext"), "push", "--force", "origin", "remote:main"],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(repo / ".snipcontext"), "checkout", "main"],
            check=True,
            capture_output=True,
        )

        # Local edits s1 differently.
        (repo / ".snipcontext" / "snippets" / "s1.json").write_text(
            json.dumps(
                {
                    "id": "s1",
                    "content": "print('local')",
                    "tags": [],
                    "updated_at": _now_iso(),
                    "deleted": False,
                }
            ),
            encoding="utf-8",
        )
        subprocess.run(
            ["git", "-C", str(repo / ".snipcontext"), "add", "-A"], check=True, capture_output=True
        )
        subprocess.run(
            ["git", "-C", str(repo / ".snipcontext"), "commit", "-m", "local: edit s1"],
            check=True,
            capture_output=True,
        )
        return repo

    def test_interactive_local_keeps_local(self, tmp_path: Path) -> None:
        repo = self._setup_conflict_repo(tmp_path)

        reset_context()
        result = runner.invoke(app, ["git", "pull", "--interactive"], input="l\n")

        assert result.exit_code == 0, result.output
        final = json.loads(
            (repo / ".snipcontext" / "snippets" / "s1.json").read_text(encoding="utf-8")
        )
        assert final["content"] == "print('local')"

    def test_interactive_remote_accepts_remote(self, tmp_path: Path) -> None:
        repo = self._setup_conflict_repo(tmp_path)

        reset_context()
        result = runner.invoke(app, ["git", "pull", "--interactive"], input="r\n")

        assert result.exit_code == 0, result.output
        final = json.loads(
            (repo / ".snipcontext" / "snippets" / "s1.json").read_text(encoding="utf-8")
        )
        assert final["content"] == "print('remote')"

    def test_interactive_abort_exits_2(self, tmp_path: Path) -> None:
        self._setup_conflict_repo(tmp_path)

        reset_context()
        result = runner.invoke(app, ["git", "pull", "--interactive"], input="a\n")

        assert result.exit_code == 2, result.output
        assert "Aborted" in result.output

    def test_non_interactive_conflict_blocks(self, tmp_path: Path) -> None:
        """CliRunner default input is non-TTY, so it should still get exit code 2."""
        self._setup_conflict_repo(tmp_path)

        reset_context()
        result = runner.invoke(app, ["git", "pull"])

        assert result.exit_code == 2, result.output
        assert "changed on both sides" in result.output
