"""CLI init command tests - extended coverage."""
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
import tempfile

from snipcontext.config.settings import Config, StorageConfig


@pytest.fixture
def tmp_dir():
    return Path(tempfile.mkdtemp())


def _invoke_cli(args, input_data=None):
    """Helper to invoke CLI commands."""
    from typer.testing import CliRunner
    from snipcontext.cli.app import app
    
    runner = CliRunner()
    return runner.invoke(app, args, input=input_data)


def test_init_with_git(tmp_dir):
    """Init with --git flag."""
    result = _invoke_cli(["init", "--local", str(tmp_dir), "--git", "--yes"])
    assert result.exit_code == 0


def test_init_with_remote(tmp_dir):
    """Init with --remote URL implies --git."""
    result = _invoke_cli(["init", "--local", str(tmp_dir), "--remote", "git@github.com:test/repo.git", "--yes"])
    assert result.exit_code == 0


def test_init_with_template(tmp_dir):
    """Init with --template copies template file."""
    template = tmp_dir / "template.json"
    template.write_text('{"title": "Test"}')
    
    result = _invoke_cli(["init", "--local", str(tmp_dir), "--template", str(template), "--yes"])
    assert result.exit_code == 0
    assert (tmp_dir / ".snipcontext" / "snippets" / "template.json").exists()


def test_init_with_template_not_found(tmp_dir):
    """Init with non-existent template shows warning."""
    result = _invoke_cli(["init", "--local", str(tmp_dir), "--template", "/nonexistent/template.json", "--yes"])
    assert result.exit_code == 0
    assert "warning" in result.output.lower() or "not found" in result.output.lower()
