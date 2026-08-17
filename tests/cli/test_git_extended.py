"""CLI git command tests - extended coverage."""

from unittest.mock import MagicMock, patch

import pytest

from snipcontext.config.settings import Config, StorageConfig


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


def _invoke_cli(args, context=None):
    """Helper to invoke CLI commands."""
    from typer.testing import CliRunner

    from snipcontext.cli.app import app

    runner = CliRunner()
    return runner.invoke(app, args)


def test_git_status_with_error(cli_context):
    """Git status handles GitError."""
    with patch("snipcontext.cli.git.GitIntegration") as mock_gi:
        from snipcontext.core.git_integration import GitError

        mock_instance = MagicMock()
        mock_instance.is_initialized.return_value = True
        mock_instance.status.side_effect = GitError("Git error")
        mock_gi.return_value = mock_instance

        result = _invoke_cli(["git", "status"])
        assert result.exit_code == 1


def test_git_pull_with_conflict(cli_context):
    """Git pull with conflicts exits with code 2."""
    with patch("snipcontext.cli.git.GitIntegration") as mock_gi:
        mock_instance = MagicMock()
        mock_instance.is_initialized.return_value = True

        mock_report = MagicMock()
        mock_report.has_conflicts = True
        mock_report.summary.return_value = "Conflict detected"
        mock_instance.detect_conflicts.return_value = mock_report
        mock_gi.return_value = mock_instance

        result = _invoke_cli(["git", "pull"])
        assert result.exit_code == 2


def test_git_pull_with_error(cli_context):
    """Git pull handles GitError."""
    with patch("snipcontext.cli.git.GitIntegration") as mock_gi:
        from snipcontext.core.git_integration import GitError

        mock_instance = MagicMock()
        mock_instance.is_initialized.return_value = True
        mock_instance.pull.side_effect = GitError("Pull failed")
        mock_gi.return_value = mock_instance

        result = _invoke_cli(["git", "pull", "--force"])
        assert result.exit_code == 1


def test_git_push_with_error(cli_context):
    """Git push handles GitError."""
    with patch("snipcontext.cli.git.GitIntegration") as mock_gi:
        from snipcontext.core.git_integration import GitError

        mock_instance = MagicMock()
        mock_instance.is_initialized.return_value = True
        mock_instance.push.side_effect = GitError("Push failed")
        mock_gi.return_value = mock_instance

        result = _invoke_cli(["git", "push"])
        assert result.exit_code == 1


def test_git_pull_no_conflict(cli_context):
    """Git pull without conflicts succeeds."""
    with patch("snipcontext.cli.git.GitIntegration") as mock_gi:
        mock_instance = MagicMock()
        mock_instance.is_initialized.return_value = True

        mock_report = MagicMock()
        mock_report.has_conflicts = False
        mock_instance.detect_conflicts.return_value = mock_report
        mock_instance.pull.return_value = "Already up to date."
        mock_gi.return_value = mock_instance

        result = _invoke_cli(["git", "pull"])
        assert result.exit_code == 0
