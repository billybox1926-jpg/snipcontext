"""CLI git command tests."""
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
import tempfile
from datetime import datetime, timezone

from snipcontext.config.settings import Config, StorageConfig
from snipcontext.core.models import Language, Snippet, SnippetMetadata


@pytest.fixture
def cli_context(tmp_path):
    """Create an isolated CLI context with temp storage."""
    storage_config = StorageConfig(data_dir=tmp_path, snippets_dir="snippets", index_dir="index")
    config = Config(
        storage=storage_config,
        search__top_k=10,
        search__default_mode="hybrid",
        search__min_score=0.0,
        search__semantic_weight=0.5,
        search__keyword_weight=0.5,
        embedding__model_name="all-MiniLM-L6-v2",
        embedding__device="cpu",
        embedding__batch_size=32,
        embedding__normalize=True,
        embedding__doc_instruction="",
        embedding__query_instruction="",
        max_snippets_per_export=100,
        snippets_per_page=20,
        watchdog_ready=False,
    )
    config.auto_tag.enabled = False
    config.dedup.enabled = False
    
    from snipcontext.core.storage import StorageEngine
    storage = StorageEngine(config)
    
    searcher = MagicMock()
    searcher.indices_ready = False
    
    return config, storage, searcher


def _invoke_cli(args, context=None, input_data=None):
    """Helper to invoke CLI commands."""
    from typer.testing import CliRunner
    from snipcontext.cli.app import app
    
    runner = CliRunner()
    if context:
        with patch("snipcontext.cli.git._get_context", return_value=context):
            return runner.invoke(app, args, input=input_data)
    return runner.invoke(app, args, input=input_data)


def test_git_status_not_initialized(cli_context):
    """Git status shows error when not initialized."""
    result = _invoke_cli(["git", "status"], cli_context)
    assert result.exit_code == 1
    assert "not a git repository" in result.output.lower()


def test_git_pull_not_initialized(cli_context):
    """Git pull shows error when not initialized."""
    result = _invoke_cli(["git", "pull"], cli_context)
    assert result.exit_code == 1
    assert "not a git repository" in result.output.lower()


def test_git_push_not_initialized(cli_context):
    """Git push shows error when not initialized."""
    result = _invoke_cli(["git", "push"], cli_context)
    assert result.exit_code == 1
    assert "not a git repository" in result.output.lower()


def test_git_status_initialized(cli_context):
    """Git status succeeds when initialized."""
    with patch("snipcontext.cli.git.GitIntegration") as mock_gi:
        mock_instance = MagicMock()
        mock_instance.is_initialized.return_value = True
        mock_instance.status.return_value = "On branch main\nnothing to commit"
        mock_gi.return_value = mock_instance
        
        result = _invoke_cli(["git", "status"], cli_context)
        assert result.exit_code == 0


def test_git_pull_force(cli_context):
    """Git pull with --force skips conflict check."""
    with patch("snipcontext.cli.git.GitIntegration") as mock_gi:
        mock_instance = MagicMock()
        mock_instance.is_initialized.return_value = True
        mock_instance.pull.return_value = "Already up to date."
        mock_gi.return_value = mock_instance
        
        result = _invoke_cli(["git", "pull", "--force"], cli_context)
        assert result.exit_code == 0
        mock_instance.pull.assert_called_once()


def test_git_push_initialized(cli_context):
    """Git push succeeds when initialized."""
    with patch("snipcontext.cli.git.GitIntegration") as mock_gi:
        mock_instance = MagicMock()
        mock_instance.is_initialized.return_value = True
        mock_instance.push.return_value = "Everything up-to-date"
        mock_gi.return_value = mock_instance
        
        result = _invoke_cli(["git", "push"], cli_context)
        assert result.exit_code == 0
        mock_instance.push.assert_called_once()
