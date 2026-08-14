"""Tests for path resolution and project-local storage discovery."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from snipcontext.cli.app import app
from snipcontext.config.paths import (
    get_config_path,
    get_storage_root,
    is_project_local,
)
from snipcontext.config.settings import get_config, reset_config

runner = CliRunner()


def _debug(label: str, **kwargs) -> None:
    """Print debug info for CI log visibility."""
    sep = "=" * 60
    print(f"\n{sep}")
    print(f"DEBUG: {label}")
    print(f"  platform: {sys.platform}")
    print(f"  python: {sys.version.split()[0]}")
    print(f"  CWD: {os.getcwd()!r}")
    for k, v in kwargs.items():
        print(f"  {k}: {v!r}")
    print(sep)


@pytest.fixture(autouse=True)
def _reset():
    reset_config()
    yield
    reset_config()


def test_get_storage_root_global(monkeypatch, tmp_path: Path):
    """No .snipcontext/, no env var -> global user_data_dir."""
    monkeypatch.delenv("SNIPCONTEXT_HOME", raising=False)
    monkeypatch.chdir(tmp_path)
    reset_config()
    root = get_storage_root()
    assert root != tmp_path / ".snipcontext"
    assert "snipcontext" in str(root).lower() or "SnipContext" in str(root)


def test_get_storage_root_project_local(tmp_path: Path):
    """Project-local .snipcontext/ in CWD -> use it."""
    (tmp_path / ".snipcontext").mkdir()
    os.chdir(tmp_path)
    reset_config()
    root = get_storage_root()
    assert root == (tmp_path / ".snipcontext").resolve()


def test_get_storage_root_parent(tmp_path: Path):
    """Project-local .snipcontext/ in parent -> found."""
    (tmp_path / ".snipcontext").mkdir()
    nested = tmp_path / "sub" / "dir"
    nested.mkdir(parents=True)
    os.chdir(nested)
    reset_config()
    root = get_storage_root()
    assert root == (tmp_path / ".snipcontext").resolve()


def test_get_storage_root_env_var(monkeypatch, tmp_path: Path):
    """SNIPCONTEXT_HOME overrides project-local and global."""
    monkeypatch.setenv("SNIPCONTEXT_HOME", str(tmp_path / "custom"))
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".snipcontext").mkdir()
    reset_config()
    root = get_storage_root()
    assert root == (tmp_path / "custom").resolve()


def test_is_project_local(tmp_path: Path):
    (tmp_path / ".snipcontext").mkdir()
    os.chdir(tmp_path)
    reset_config()
    assert is_project_local() is True
    os.chdir(Path.home())
    reset_config()
    assert is_project_local() is False


def test_get_config_path_project_local(tmp_path: Path):
    (tmp_path / ".snipcontext").mkdir()
    os.chdir(tmp_path)
    reset_config()
    assert get_config_path() == (tmp_path / ".snipcontext" / "config.yaml").resolve()


def test_init_creates_directory(tmp_path: Path):
    _debug("test_init_creates_directory", tmp_path=tmp_path)
    os.chdir(tmp_path)
    result = runner.invoke(app, ["init"])
    print(f"  exit_code: {result.exit_code}")
    print(f"  output: {result.output!r}")
    if result.exception:
        print(f"  exception: {result.exception!r}")
    assert result.exit_code == 0, result.output
    target = tmp_path / ".snipcontext"
    assert target.is_dir()
    assert (target / "snippets").is_dir()
    assert (target / "config.json").is_file()
    assert (target / ".gitignore").is_file()
    assert "index.faiss" in (target / ".gitignore").read_text()


def test_init_fails_if_exists(tmp_path: Path):
    _debug("test_init_fails_if_exists", tmp_path=tmp_path)
    (tmp_path / ".snipcontext").mkdir()
    os.chdir(tmp_path)
    result = runner.invoke(app, ["init"])
    print(f"  exit_code: {result.exit_code}")
    print(f"  output: {result.output!r}")
    if result.exception:
        print(f"  exception: {result.exception!r}")
    assert result.exit_code != 0


def test_init_with_local_path(tmp_path: Path):
    _debug("test_init_with_local_path", tmp_path=tmp_path)
    custom_path = tmp_path / "custom"
    result = runner.invoke(app, ["init", "--local", str(custom_path)])
    print(f"  exit_code: {result.exit_code}")
    print(f"  output: {result.output!r}")
    if result.exception:
        print(f"  exception: {result.exception!r}")
    assert result.exit_code == 0
    target = custom_path / ".snipcontext"
    assert target.is_dir()
    assert (target / "config.json").is_file()


def test_init_with_force(tmp_path: Path):
    _debug("test_init_with_force", tmp_path=tmp_path)
    target = tmp_path / ".snipcontext"
    target.mkdir()
    (target / "old.txt").write_text("old")
    os.chdir(tmp_path)
    result = runner.invoke(app, ["init", "--force"])
    print(f"  exit_code: {result.exit_code}")
    print(f"  output: {result.output!r}")
    if result.exception:
        print(f"  exception: {result.exception!r}")
    assert result.exit_code == 0
    assert (target / "config.json").is_file()
    assert (target / "old.txt").is_file()


def test_init_with_template(tmp_path: Path):
    _debug("test_init_with_template", tmp_path=tmp_path)
    template = tmp_path / "example.json"
    template.write_text('{"code": "print(1)"}')
    os.chdir(tmp_path)
    result = runner.invoke(app, ["init", "--template", str(template)])
    print(f"  exit_code: {result.exit_code}")
    print(f"  output: {result.output!r}")
    if result.exception:
        print(f"  exception: {result.exception!r}")
    assert result.exit_code == 0
    target = tmp_path / ".snipcontext"
    assert (target / "snippets" / "example.json").is_file()


def test_init_git_creates_repo(tmp_path: Path) -> None:
    _debug("test_init_git_creates_repo", tmp_path=tmp_path)
    os.chdir(tmp_path)
    result = runner.invoke(app, ["init", "--git"])
    print(f"  exit_code: {result.exit_code}")
    print(f"  output: {result.output!r}")
    if result.exception:
        print(f"  exception: {result.exception!r}")
    assert result.exit_code == 0, result.output
    target = tmp_path / ".snipcontext"
    assert (target / ".git").is_dir()
    assert (target / ".gitignore").is_file()
    assert (target / "config.json").is_file()
    assert (target / "snippets").is_dir()
    assert any(
        "initialize SnipContext storage" in line
        for line in _run(["log", "--oneline"], target).stdout.splitlines()
    )


def test_init_git_with_remote(tmp_path: Path) -> None:
    _debug("test_init_git_with_remote", tmp_path=tmp_path)
    os.chdir(tmp_path)
    result = runner.invoke(app, ["init", "--git", "--remote", "https://example.com/repo.git"])
    print(f"  exit_code: {result.exit_code}")
    print(f"  output: {result.output!r}")
    if result.exception:
        print(f"  exception: {result.exception!r}")
    assert result.exit_code == 0, result.output
    target = tmp_path / ".snipcontext"
    remote_output = _run(["remote", "get-url", "origin"], target).stdout.strip()
    assert remote_output == "https://example.com/repo.git"


def test_init_git_fails_without_git(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _debug("test_init_git_fails_without_git", tmp_path=tmp_path)
    monkeypatch.setattr("shutil.which", lambda name: None if name == "git" else True)
    os.chdir(tmp_path)
    result = runner.invoke(app, ["init", "--git"])
    print(f"  exit_code: {result.exit_code}")
    print(f"  output: {result.output!r}")
    if result.exception:
        print(f"  exception: {result.exception!r}")
    assert result.exit_code != 0
    assert "git" in result.output.lower()


def _run(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True, check=False)


def test_storage_engine_uses_resolved_root(tmp_path: Path):
    from snipcontext.core.storage import StorageEngine

    _debug("test_storage_engine_uses_resolved_root", tmp_path=tmp_path)
    (tmp_path / ".snipcontext").mkdir()
    os.chdir(tmp_path)
    reset_config()
    config = get_config()
    storage = StorageEngine(config)
    assert storage.snippets_dir == tmp_path / ".snipcontext" / "snippets"
    assert storage.index_dir == tmp_path / ".snipcontext" / "index"


def test_config_file_is_loaded(tmp_path: Path):
    _debug("test_config_file_is_loaded", tmp_path=tmp_path)
    os.chdir(tmp_path)
    result = runner.invoke(app, ["init"])
    print(f"  exit_code: {result.exit_code}")
    print(f"  output: {result.output!r}")
    if result.exception:
        print(f"  exception: {result.exception!r}")
        import traceback

        traceback.print_exception(
            type(result.exception), result.exception, result.exception.__traceback__
        )
    assert result.exit_code == 0, result.output
    reset_config()
    config = get_config()
    print(f"  config.storage.snippets_dir: {config.storage.snippets_dir!r}")
    print(f"  config.storage.index_dir: {config.storage.index_dir!r}")
    print(f"  config.storage.data_dir: {config.storage.data_dir!r}")
    expected_data_dir = (tmp_path / ".snipcontext").resolve()
    print(f"  expected_data_dir: {expected_data_dir!r}")
    print(f"  match: {config.storage.data_dir == expected_data_dir}")
    assert config.storage.snippets_dir == "snippets"
    assert config.storage.index_dir == "index"
    assert config.storage.data_dir == expected_data_dir
