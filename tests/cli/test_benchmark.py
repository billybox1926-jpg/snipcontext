"""CLI benchmark command tests."""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from snipcontext.cli.app import app


@pytest.fixture()
def runner():
    return CliRunner()


def test_benchmark_index_help(runner):
    result = runner.invoke(app, ["benchmark", "index", "--help"])
    assert result.exit_code == 0
    assert "Benchmark vector index build" in result.stdout


@pytest.mark.slow
def test_benchmark_index_smoke(runner, caplog):
    caplog.set_level("INFO")
    result = runner.invoke(
        app,
        [
            "benchmark",
            "index",
            "--vectors",
            "200",
            "--dim",
            "16",
            "--index-type",
            "flat",
        ],
    )
    assert result.exit_code == 0, result.stdout + result.stderr
    assert "Vector index benchmark" in result.stdout


def test_benchmark_index_no_auto_switch(runner, caplog):
    caplog.set_level("INFO")
    result = runner.invoke(
        app,
        [
            "benchmark",
            "index",
            "--vectors",
            "200",
            "--dim",
            "16",
            "--index-type",
            "flat",
            "--no-auto-switch",
        ],
    )
    assert result.exit_code == 0, result.stdout + result.stderr
    assert "Vector index benchmark" in result.stdout
