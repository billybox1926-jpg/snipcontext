"""CLI info command tests."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch


def _invoke_cli(args):
    """Helper to invoke CLI commands."""
    from typer.testing import CliRunner
    from snipcontext.cli.app import app

    runner = CliRunner()
    return runner.invoke(app, args)


def test_info_command():
    """Info command shows configuration."""
    result = _invoke_cli(["info"])
    assert result.exit_code == 0
    assert "snipcontext" in result.output.lower() or "configuration" in result.output.lower()


def test_info_command_content():
    """Info command shows storage paths."""
    result = _invoke_cli(["info"])
    assert result.exit_code == 0
    # Should show some path information
    output = result.output.lower()
    assert "storage" in output or "root" in output or "mode" in output
