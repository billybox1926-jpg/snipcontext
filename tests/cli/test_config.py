"""Config CLI tests."""

from __future__ import annotations

import pytest
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
import tempfile
from pathlib import Path

import yaml
from typer.testing import CliRunner

from snipcontext.cli.app import app

runner = CliRunner()


def test_config_init_creates_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"
        result = runner.invoke(app, ["config", "init", "--path", str(config_path)])
        assert result.exit_code == 0, result.stdout + result.stderr
        assert config_path.exists()
        data = yaml.safe_load(config_path.read_text())
        assert "storage" in data or "embedding" in data


def test_config_init_refuses_overwrite():
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"
        config_path.touch()
        result = runner.invoke(app, ["config", "init", "--path", str(config_path)])
        assert result.exit_code == 0, result.stdout + result.stderr
        assert "already exists" in result.output or "overwrite" in result.output
        assert config_path.read_text() == ""


def test_config_init_force_overwrites():
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"
        config_path.write_text("old: data")
        result = runner.invoke(app, ["config", "init", "--path", str(config_path), "--force"])
        assert result.exit_code == 0, result.stdout + result.stderr
        data = yaml.safe_load(config_path.read_text())
        assert "old" not in data
        assert "storage" in data or "embedding" in data
