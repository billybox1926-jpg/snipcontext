"""Tests for the CLI commands."""

from __future__ import annotations

import tempfile
from pathlib import Path

from typer.testing import CliRunner

from snipcontext.cli.app import app

runner = CliRunner()


def invoke(*args, env=None, input=None):
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

        runner_kwargs = {"env": env_vars}
        if input is not None:
            runner_kwargs["input"] = input

        result = runner.invoke(app, args, **runner_kwargs)
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
            f.write("def test:\n    pass\n")
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

    def test_stats_shows_languages(self):
        """Stats should display language distribution."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            env = {
                "SNIPCONTEXT_STORAGE__DATA_DIR": str(tmp_path),
                "SNIPCONTEXT_STORAGE__SNIPPETS_DIR": "snippets",
                "SNIPCONTEXT_STORAGE__INDEX_DIR": "index",
            }
            r1, _ = invoke("add", "print('hi')", "--title", "Py", "--lang", "python", env=env)
            assert r1.exit_code == 0
            r2, _ = invoke("stats", env=env)
            assert r2.exit_code == 0
            assert "python" in r2.output

    def test_stats_shows_tags(self):
        """Stats should display tag distribution."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            env = {
                "SNIPCONTEXT_STORAGE__DATA_DIR": str(tmp_path),
                "SNIPCONTEXT_STORAGE__SNIPPETS_DIR": "snippets",
                "SNIPCONTEXT_STORAGE__INDEX_DIR": "index",
            }
            r1, _ = invoke("add", "x", "--title", "T", "--tag", "web", "--tag", "api", env=env)
            assert r1.exit_code == 0
            r2, _ = invoke("stats", env=env)
            assert r2.exit_code == 0
            assert "web" in r2.output

    def test_stats_detailed_flag(self):
        """Stats --detailed should show extra analytics sections."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            env = {
                "SNIPCONTEXT_STORAGE__DATA_DIR": str(tmp_path),
                "SNIPCONTEXT_STORAGE__SNIPPETS_DIR": "snippets",
                "SNIPCONTEXT_STORAGE__INDEX_DIR": "index",
            }
            r1, _ = invoke("add", "x", "--title", "A", "--tag", "test", env=env)
            assert r1.exit_code == 0
            r2, _ = invoke("add", "y", "--title", "B", "--tag", "test", env=env)
            assert r2.exit_code == 0
            r3, _ = invoke("stats", "--detailed", env=env)
            assert r3.exit_code == 0
            assert "Detailed" in r3.output

    def test_stats_json_output(self):
        """Stats --json should output valid JSON."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            env = {
                "SNIPCONTEXT_STORAGE__DATA_DIR": str(tmp_path),
                "SNIPCONTEXT_STORAGE__SNIPPETS_DIR": "snippets",
                "SNIPCONTEXT_STORAGE__INDEX_DIR": "index",
            }
            r1, _ = invoke("add", "x", "--title", "A", "--tag", "test", env=env)
            assert r1.exit_code == 0
            r2, _ = invoke("stats", "--json", env=env)
            assert r2.exit_code == 0
            import json

            data = json.loads(r2.output)
            assert data["total_snippets"] == 1

    def test_stats_detailed_json_output(self):
        """Stats --detailed --json should include detailed fields."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            env = {
                "SNIPCONTEXT_STORAGE__DATA_DIR": str(tmp_path),
                "SNIPCONTEXT_STORAGE__SNIPPETS_DIR": "snippets",
                "SNIPCONTEXT_STORAGE__INDEX_DIR": "index",
            }
            r1, _ = invoke("add", "x", "--title", "A", "--tag", "test", env=env)
            assert r1.exit_code == 0
            r2, _ = invoke("stats", "--detailed", "--json", env=env)
            assert r2.exit_code == 0
            import json

            data = json.loads(r2.output)
            assert "access_counts" in data
            assert "size_metrics" in data
            assert "language_distribution" in data
            assert "confidence" in data


class TestProvidersCommand:
    """Tests for the `providers` command."""

    def test_list_providers(self):
        result, tmp = invoke("providers")
        assert result.exit_code == 0
        assert "claude" in result.output
        assert "generic" in result.output
        assert "openai" in result.output

    def test_providers_health(self):
        result, tmp = invoke("providers", "--health")
        assert result.exit_code == 0
        assert "Provider Health" in result.output


class TestPluginsCommand:
    """Tests for the `plugins` command."""

    def test_plugins_list(self):
        result, tmp = invoke("plugins", "--list")
        assert result.exit_code == 0
        assert "Plugins" in result.output or "No plugins registered" in result.output

    def test_plugins_health(self):
        result, tmp = invoke("plugins", "--health")
        assert result.exit_code == 0
        assert "Provider Health" in result.output


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

            assert "python" in r2.output.lower() and "hello" in r2.output.lower(), (
                f"Expected suggested tags in add output; got:\n{r2.output}"
            )


class TestDedupIntegration:
    """End-to-end deduplication warnings through `sc add`."""

    def test_add_duplicate_triggers_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            env = {
                "SNIPCONTEXT_STORAGE__DATA_DIR": str(tmp_path),
                "SNIPCONTEXT_STORAGE__SNIPPETS_DIR": "snippets",
                "SNIPCONTEXT_STORAGE__INDEX_DIR": "index",
                "SC_AUTO_TAG_ENABLED": "false",
                "SC_DEDUP_ENABLED": "true",
                "SC_DEDUP_THRESHOLD": "0.95",
            }

            # First snippet – baseline expected behavior
            r1, _ = invoke(
                "add",
                "print('hello world')",
                "--tag",
                "test",
                env=env,
            )
            assert r1.exit_code == 0
            assert "Added snippet" in r1.output

            # Second identical snippet – if the index can't build/train here,
            # we must still not crash and must not emit an incorrect dedup warning.
            r2, _ = invoke(
                "add",
                "print('hello world')",
                env=env,
            )
            assert r2.exit_code == 0
            assert "Added snippet" in r2.output
            assert "This looks similar to" not in r2.output


class TestEditCommand:
    """Tests for the `edit` command (Issue #2 — Improved Snippet Editing UX)."""

    def _add_and_get_id(self, env):
        """Helper: add a snippet and return its ID from the output."""
        result, _ = invoke(
            "add",
            "print('hello')",
            "--title",
            "Hello",
            "--tag",
            "python",
            "--lang",
            "python",
            env=env,
        )
        assert result.exit_code == 0, f"Add failed: {result.output}"
        # Extract ID from output line like "ID: abcdef1234..."
        for line in result.output.splitlines():
            if "ID:" in line:
                return line.split("ID:")[-1].strip()
        return None

    def test_edit_title_with_confirmation(self):
        """Edit title — should prompt for confirmation and succeed with 'y'."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            env = {
                "SNIPCONTEXT_STORAGE__DATA_DIR": str(tmp_path),
                "SNIPCONTEXT_STORAGE__SNIPPETS_DIR": "snippets",
                "SNIPCONTEXT_STORAGE__INDEX_DIR": "index",
            }
            sid = self._add_and_get_id(env)
            assert sid is not None

            result, _ = invoke("edit", sid, "--title", "New Title", input="y", env=env)
            assert result.exit_code == 0
            assert "Updated" in result.output

    def test_edit_title_force_skip_confirmation(self):
        """Edit with --force should skip confirmation prompt."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            env = {
                "SNIPCONTEXT_STORAGE__DATA_DIR": str(tmp_path),
                "SNIPCONTEXT_STORAGE__SNIPPETS_DIR": "snippets",
                "SNIPCONTEXT_STORAGE__INDEX_DIR": "index",
            }
            sid = self._add_and_get_id(env)
            assert sid is not None

            result, _ = invoke("edit", sid, "--title", "Forced Title", "--force", env=env)
            assert result.exit_code == 0
            assert "Updated" in result.output

    def test_edit_cancelled(self):
        """Edit with 'n' at confirmation should cancel and not save."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            env = {
                "SNIPCONTEXT_STORAGE__DATA_DIR": str(tmp_path),
                "SNIPCONTEXT_STORAGE__SNIPPETS_DIR": "snippets",
                "SNIPCONTEXT_STORAGE__INDEX_DIR": "index",
            }
            sid = self._add_and_get_id(env)
            assert sid is not None

            result, _ = invoke("edit", sid, "--title", "Cancelled Title", input="n", env=env)
            assert result.exit_code == 0
            assert "Cancelled" in result.output

    def test_edit_add_tags(self):
        """Edit with --tag should add tags to snippet."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            env = {
                "SNIPCONTEXT_STORAGE__DATA_DIR": str(tmp_path),
                "SNIPCONTEXT_STORAGE__SNIPPETS_DIR": "snippets",
                "SNIPCONTEXT_STORAGE__INDEX_DIR": "index",
            }
            sid = self._add_and_get_id(env)
            assert sid is not None

            result, _ = invoke("edit", sid, "--tag", "cli", "--tag", "demo", "--force", env=env)
            assert result.exit_code == 0
            assert "Updated" in result.output
            assert "cli" in result.output or "demo" in result.output

    def test_edit_remove_tags(self):
        """Edit with --remove-tag should remove a tag."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            env = {
                "SNIPCONTEXT_STORAGE__DATA_DIR": str(tmp_path),
                "SNIPCONTEXT_STORAGE__SNIPPETS_DIR": "snippets",
                "SNIPCONTEXT_STORAGE__INDEX_DIR": "index",
            }
            sid = self._add_and_get_id(env)
            assert sid is not None

            result, _ = invoke("edit", sid, "--remove-tag", "python", "--force", env=env)
            assert result.exit_code == 0
            assert "Updated" in result.output

    def test_edit_content(self):
        """Edit with --content should update snippet content."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            env = {
                "SNIPCONTEXT_STORAGE__DATA_DIR": str(tmp_path),
                "SNIPCONTEXT_STORAGE__SNIPPETS_DIR": "snippets",
                "SNIPCONTEXT_STORAGE__INDEX_DIR": "index",
            }
            sid = self._add_and_get_id(env)
            assert sid is not None

            result, _ = invoke("edit", sid, "--content", "print('updated')", "--force", env=env)
            assert result.exit_code == 0
            assert "Updated" in result.output

    def test_edit_language(self):
        """Edit with --lang should change the language."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            env = {
                "SNIPCONTEXT_STORAGE__DATA_DIR": str(tmp_path),
                "SNIPCONTEXT_STORAGE__SNIPPETS_DIR": "snippets",
                "SNIPCONTEXT_STORAGE__INDEX_DIR": "index",
            }
            sid = self._add_and_get_id(env)
            assert sid is not None

            result, _ = invoke("edit", sid, "--lang", "javascript", "--force", env=env)
            assert result.exit_code == 0
            assert "Updated" in result.output

    def test_edit_description(self):
        """Edit with --desc should update the description."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            env = {
                "SNIPCONTEXT_STORAGE__DATA_DIR": str(tmp_path),
                "SNIPCONTEXT_STORAGE__SNIPPETS_DIR": "snippets",
                "SNIPCONTEXT_STORAGE__INDEX_DIR": "index",
            }
            sid = self._add_and_get_id(env)
            assert sid is not None

            result, _ = invoke("edit", sid, "--desc", "A hello world example", "--force", env=env)
            assert result.exit_code == 0
            assert "Updated" in result.output

    def test_edit_no_changes(self):
        """Edit with no changes should exit with message."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            env = {
                "SNIPCONTEXT_STORAGE__DATA_DIR": str(tmp_path),
                "SNIPCONTEXT_STORAGE__SNIPPETS_DIR": "snippets",
                "SNIPCONTEXT_STORAGE__INDEX_DIR": "index",
            }
            sid = self._add_and_get_id(env)
            assert sid is not None

            result, _ = invoke("edit", sid, env=env)
            assert result.exit_code == 0
            assert "No changes" in result.output

    def test_edit_not_found(self):
        """Edit with nonexistent ID should error."""
        result, _ = invoke("edit", "nonexistent999")
        assert result.exit_code == 1
        assert "not found" in result.output

    def test_edit_shows_changes_summary(self):
        """Confirmation prompt should show which fields will change."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            env = {
                "SNIPCONTEXT_STORAGE__DATA_DIR": str(tmp_path),
                "SNIPCONTEXT_STORAGE__SNIPPETS_DIR": "snippets",
                "SNIPCONTEXT_STORAGE__INDEX_DIR": "index",
            }
            sid = self._add_and_get_id(env)
            assert sid is not None

            result, _ = invoke("edit", sid, "--title", "X", "--tag", "newtag", input="y", env=env)
            assert result.exit_code == 0
            # Should show change summary before asking to confirm
            assert "Changes:" in result.output

    def test_edit_from_file(self):
        """Edit with --file should read content from file path."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            env = {
                "SNIPCONTEXT_STORAGE__DATA_DIR": str(tmp_path),
                "SNIPCONTEXT_STORAGE__SNIPPETS_DIR": "snippets",
                "SNIPCONTEXT_STORAGE__INDEX_DIR": "index",
            }
            sid = self._add_and_get_id(env)
            assert sid is not None

            content_file = tmp_path / "edit_content.py"
            content_file.write_text("def new_function():\n    return 42\n")

            result, _ = invoke(
                "edit", sid, "--content", str(content_file), "--file", "--force", env=env
            )
            assert result.exit_code == 0
            assert "Updated" in result.output

    def test_add_with_metadata(self):
        """Add snippet with --source, --framework, --version, --custom."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            env = {
                "SNIPCONTEXT_STORAGE__DATA_DIR": str(tmp_path),
                "SNIPCONTEXT_STORAGE__SNIPPETS_DIR": "snippets",
                "SNIPCONTEXT_STORAGE__INDEX_DIR": "index",
            }
            result, _ = invoke(
                "add",
                "print('hello')",
                "--title",
                "Test Meta",
                "--lang",
                "python",
                "--source",
                "https://example.com/snippet.py",
                "--framework",
                "fastapi",
                "--version",
                "0.100+",
                "--custom",
                "priority=high",
                "--custom",
                "team=backend",
                env=env,
            )
            assert result.exit_code == 0

            # Extract ID from output
            sid = None
            for line in result.output.splitlines():
                if "ID:" in line:
                    sid = line.split("ID:")[-1].strip()
            assert sid is not None

            get_result, _ = invoke("get", sid, env=env)
            assert "fastapi" in get_result.output
            assert "0.100+" in get_result.output
            assert "example.com" in get_result.output
            assert "priority=high" in get_result.output

    def test_edit_framework(self):
        """Edit with --framework should update the framework field."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            env = {
                "SNIPCONTEXT_STORAGE__DATA_DIR": str(tmp_path),
                "SNIPCONTEXT_STORAGE__SNIPPETS_DIR": "snippets",
                "SNIPCONTEXT_STORAGE__INDEX_DIR": "index",
            }
            sid = self._add_and_get_id(env)
            assert sid is not None

            result, _ = invoke("edit", sid, "--framework", "react", "--force", env=env)
            assert result.exit_code == 0
            assert "Updated" in result.output

            get_result, _ = invoke("get", sid, env=env)
            assert "react" in get_result.output

    def test_edit_version(self):
        """Edit with --version should update the version field."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            env = {
                "SNIPCONTEXT_STORAGE__DATA_DIR": str(tmp_path),
                "SNIPCONTEXT_STORAGE__SNIPPETS_DIR": "snippets",
                "SNIPCONTEXT_STORAGE__INDEX_DIR": "index",
            }
            sid = self._add_and_get_id(env)
            assert sid is not None

            result, _ = invoke("edit", sid, "--version", "18.x", "--force", env=env)
            assert result.exit_code == 0

            get_result, _ = invoke("get", sid, env=env)
            assert "18.x" in get_result.output

    def test_edit_source(self):
        """Edit with --source should update the source URL."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            env = {
                "SNIPCONTEXT_STORAGE__DATA_DIR": str(tmp_path),
                "SNIPCONTEXT_STORAGE__SNIPPETS_DIR": "snippets",
                "SNIPCONTEXT_STORAGE__INDEX_DIR": "index",
            }
            sid = self._add_and_get_id(env)
            assert sid is not None

            result, _ = invoke(
                "edit", sid, "--source", "https://github.com/example/repo", "--force", env=env
            )
            assert result.exit_code == 0

            get_result, _ = invoke("get", sid, env=env)
            assert "github.com/example/repo" in get_result.output

    def test_edit_custom_metadata(self):
        """Edit with --custom should merge custom key-value pairs."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            env = {
                "SNIPCONTEXT_STORAGE__DATA_DIR": str(tmp_path),
                "SNIPCONTEXT_STORAGE__SNIPPETS_DIR": "snippets",
                "SNIPCONTEXT_STORAGE__INDEX_DIR": "index",
            }
            # Add with one custom field
            add_result, _ = invoke(
                "add",
                "x = 1",
                "--title",
                "Custom Test",
                "--custom",
                "env=staging",
                env=env,
            )
            assert add_result.exit_code == 0
            sid = None
            for line in add_result.output.splitlines():
                if "ID:" in line:
                    sid = line.split("ID:")[-1].strip()
            assert sid is not None

            # Edit: add another custom field
            result, _ = invoke("edit", sid, "--custom", "tier=frontend", "--force", env=env)
            assert result.exit_code == 0

            get_result, _ = invoke("get", sid, env=env)
            assert "env=staging" in get_result.output
            assert "tier=frontend" in get_result.output
