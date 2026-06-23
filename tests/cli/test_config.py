"""Config CLI tests."""

from __future__ import annotations

import pytest
from snipcontext.cli.app import app
from typer.testing import CliRunner


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
