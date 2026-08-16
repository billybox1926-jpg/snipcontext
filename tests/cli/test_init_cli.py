"""CLI init command tests."""
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


def test_init_basic(tmp_dir):
    """Init command creates .snipcontext directory."""
    result = _invoke_cli(["init", "--local", str(tmp_dir), "--yes"])
    assert result.exit_code == 0
    assert (tmp_dir / ".snipcontext").exists()


def test_init_creates_snippets_dir(tmp_dir):
    """Init creates snippets subdirectory."""
    result = _invoke_cli(["init", "--local", str(tmp_dir), "--yes"])
    assert result.exit_code == 0
    assert (tmp_dir / ".snipcontext" / "snippets").exists()


def test_init_creates_config(tmp_dir):
    """Init creates config.json."""
    result = _invoke_cli(["init", "--local", str(tmp_dir), "--yes"])
    assert result.exit_code == 0
    assert (tmp_dir / ".snipcontext" / "config.json").exists()


def test_init_existing_no_force(tmp_dir):
    """Init without --force on existing dir shows error."""
    # Create existing .snipcontext
    (tmp_dir / ".snipcontext").mkdir(parents=True, exist_ok=True)
    
    result = _invoke_cli(["init", "--local", str(tmp_dir)])
    assert result.exit_code == 1
    assert "already exists" in result.output.lower() or "error" in result.output.lower()


def test_init_force_overwrites(tmp_dir):
    """Init with --force overwrites existing."""
    # Create existing .snipcontext
    (tmp_dir / ".snipcontext").mkdir(parents=True, exist_ok=True)
    
    result = _invoke_cli(["init", "--local", str(tmp_dir), "--force"])
    assert result.exit_code == 0


def test_init_from_stdin(tmp_dir):
    """Init reads path from stdin."""
    result = _invoke_cli(["init"], input_data=str(tmp_dir))
    assert result.exit_code == 0
    assert (tmp_dir / ".snipcontext").exists()
