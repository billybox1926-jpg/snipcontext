"""Tests for the CLI commands."""

from __future__ import annotations

import tempfile
from pathlib import Path

from snipcontext.cli.main import app
from typer.testing import CliRunner

runner = CliRunner()


def invoke(*args, env=None):
    """Helper to invoke CLI commands."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        env_vars = {
            "SNIPCONTEXT_STORAGE__DATA_DIR": str(tmp_path),
            "SNIPCONTEXT_STORAGE__SNIPPETS_DIR": "snippets",
            "SNIPCONTEXT_STORAGE__INDEX_DIR": "index",
        }
        if env:
            env_vars.update(env)

        result = runner.invoke(app, args, env=env_vars)
        return result, tmp_path


class TestAddCommand:
    """Tests for the `add` command."""

    def test_add_snippet(self):
        result, tmp = invoke(
            "add", "print('hello')", "--title", "Hello", "--tag", "python", "--tag", "demo"
        )
        assert result.exit_code == 0
        assert "Added snippet" in result.output

    def test_add_from_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("def test():\n    pass\n")
            f.flush()
            result, tmp = invoke("add", f.name, "--file", "--title", "Test File", "--tag", "python")
            assert result.exit_code == 0
            assert "Added snippet" in result.output

    def test_add_auto_title(self):
        result, tmp = invoke("add", "def auto_title(): pass", "--tag", "python")
        assert result.exit_code == 0


class TestListCommand:
    """Tests for the `list` command."""

    def test_list_with_snippets(self):
        # Must use same temp directory for both calls
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            env = {
                "SNIPCONTEXT_STORAGE__DATA_DIR": str(tmp_path),
                "SNIPCONTEXT_STORAGE__SNIPPETS_DIR": "snippets",
                "SNIPCONTEXT_STORAGE__INDEX_DIR": "index",
            }
            r1, _ = invoke("add", "print('x')", "--title", "Test", "--tag", "python", env=env)
            assert r1.exit_code == 0
            r2, _ = invoke("list", env=env)
            assert r2.exit_code == 0
            assert "Test" in r2.output


class TestGetCommand:
    """Tests for the `get` command."""

    def test_get_not_found(self):
        result, tmp = invoke("get", "nonexistent123")
        assert result.exit_code == 1


class TestStatsCommand:
    """Tests for the `stats` command."""

    def test_empty_stats(self):
        result, tmp = invoke("stats")
        assert result.exit_code == 0

    def test_with_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            env = {
                "SNIPCONTEXT_STORAGE__DATA_DIR": str(tmp_path),
                "SNIPCONTEXT_STORAGE__SNIPPETS_DIR": "snippets",
                "SNIPCONTEXT_STORAGE__INDEX_DIR": "index",
            }
            r1, _ = invoke("add", "x", "--title", "A", "--tag", "python", env=env)
            assert r1.exit_code == 0
            r2, _ = invoke("add", "y", "--title", "B", "--tag", "python", env=env)
            assert r2.exit_code == 0
            r3, _ = invoke("stats", env=env)
            assert r3.exit_code == 0
            assert "2" in r3.output


class TestProvidersCommand:
    """Tests for the `providers` command."""

    def test_list_providers(self):
        result, tmp = invoke("providers")
        assert result.exit_code == 0
        assert "claude" in result.output
        assert "generic" in result.output
        assert "openai" in result.output


class TestConfigCommands:
    """Tests for config subcommands."""

    def test_config_path(self):
        result, tmp = invoke("config", "path")
        assert result.exit_code == 0
        assert "Data dir" in result.output


class TestAutoTagIntegration:
    """End-to-end auto-tag suggestions through `sc add`."""

    def test_add_auto_tag_suggestion(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            env = {
                "SNIPCONTEXT_STORAGE__DATA_DIR": str(tmp_path),
                "SNIPCONTEXT_STORAGE__SNIPPETS_DIR": "snippets",
                "SNIPCONTEXT_STORAGE__INDEX_DIR": "index",
                "SC_AUTO_TAG_ENABLED": "true",
                "SC_AUTO_TAG_TOP_K": "3",
                "SC_AUTO_TAG_MIN_FREQUENCY": "1",
                "SC_AUTO_TAG_AUTO_ACCEPT": "true",
            }

            r1, _ = invoke(
                "add",
                "print('hello world')",
                "--tag",
                "python",
                "--tag",
                "hello",
                env=env,
            )
            assert r1.exit_code == 0

            r2, _ = invoke(
                "add",
                "print('hello python')",
                env=env,
            )
            assert r2.exit_code == 0

            assert (
                "python" in r2.output.lower() and "hello" in r2.output.lower()
            ), f"Expected suggested tags in add output; got:\n{r2.output}"
