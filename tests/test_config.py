"""Tests for path resolution and project-local storage discovery."""

from __future__ import annotations

import os
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


def test_init_local_creates_directory(tmp_path: Path):
    os.chdir(tmp_path)
    result = runner.invoke(app, ["init", "--local"])
    assert result.exit_code == 0, result.output
    target = tmp_path / ".snipcontext"
    assert target.is_dir()
    assert (target / "snippets").is_dir()
    assert (target / "config.yaml").is_file()
    assert (target / ".gitignore").is_file()
    assert "index.faiss" in (target / ".gitignore").read_text()


def test_init_local_fails_if_exists(tmp_path: Path):
    (tmp_path / ".snipcontext").mkdir()
    os.chdir(tmp_path)
    result = runner.invoke(app, ["init", "--local"])
    assert result.exit_code != 0


def test_storage_engine_uses_resolved_root(tmp_path: Path):
    from snipcontext.core.storage import StorageEngine

    (tmp_path / ".snipcontext").mkdir()
    os.chdir(tmp_path)
    reset_config()
    config = get_config()
    storage = StorageEngine(config)
    assert storage.snippets_dir == tmp_path / ".snipcontext" / "snippets"
    assert storage.index_dir == tmp_path / ".snipcontext" / "index"


def test_config_file_is_loaded(tmp_path: Path):
    os.chdir(tmp_path)
    result = runner.invoke(app, ["init", "--local"])
    assert result.exit_code == 0, result.output
    reset_config()
    config = get_config()
    assert config.storage.snippets_dir == "snippets"
    assert config.storage.index_dir == "index"
    assert config.storage.data_dir == (tmp_path / ".snipcontext").resolve()
