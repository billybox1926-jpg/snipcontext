"""Config CLI tests."""

from __future__ import annotations

import os

import pytest
import yaml
from typer.testing import CliRunner

from snipcontext.cli.app import app


@pytest.fixture()
def runner():
    return CliRunner()


def test_config_list(runner):
    result = runner.invoke(app, ["config", "list"])
    assert result.exit_code == 0, result.stdout + result.stderr
    assert "Configuration keys" in result.stdout
    assert "search.index_type" in result.stdout


def test_config_set(runner):
    result = runner.invoke(app, ["config", "set", "search.index_type", "flat", "--no-save"])
    assert result.exit_code == 0, result.stdout + result.stderr
    assert "Set search.index_type = flat" in result.stdout


def test_config_set_invalid_key(runner):
    result = runner.invoke(app, ["config", "set", "nonexistent.key", "value", "--no-save"])
    assert result.exit_code != 0


def test_config_init_creates_file(runner, monkeypatch, tmp_path):
    project = tmp_path / "proj"
    project.mkdir()
    (project / ".snipcontext").mkdir()
    monkeypatch.chdir(project)
    result = runner.invoke(app, ["config", "init"])
    assert result.exit_code == 0, result.stdout + result.stderr
    config_path = project / ".snipcontext" / "config.yaml"
    assert config_path.exists()
    data = yaml.safe_load(config_path.read_text())
    assert "storage" in data or "embedding" in data


def test_config_init_refuses_overwrite(runner, monkeypatch, tmp_path):
    project = tmp_path / "proj"
    project.mkdir()
    (project / ".snipcontext").mkdir()
    config_path = project / ".snipcontext" / "config.yaml"
    config_path.write_text("old: data")
    monkeypatch.chdir(project)
    result = runner.invoke(app, ["config", "init"])
    assert result.exit_code == 0, result.stdout + result.stderr
    assert (
        "already exists" in result.output
        or "overwrite" in result.output
        or "Use --force" in result.output
    )
    assert config_path.read_text() == "old: data"


def test_config_init_force_overwrites(runner, monkeypatch, tmp_path):
    project = tmp_path / "proj"
    project.mkdir()
    (project / ".snipcontext").mkdir()
    config_path = project / ".snipcontext" / "config.yaml"
    config_path.write_text("old: data")
    monkeypatch.chdir(project)
    result = runner.invoke(app, ["config", "init", "--force"])
    assert result.exit_code == 0, result.stdout + result.stderr
    data = yaml.safe_load(config_path.read_text())
    assert "old" not in data
    assert "storage" in data or "embedding" in data
