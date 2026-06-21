"""Tests for TUI command parsing and registry."""

from __future__ import annotations

from snipcontext.tui.commands import CommandRegistry, _parse_args


class TestParseArgs:
    def test_positional_only(self):
        args, kwargs = _parse_args(["hello", "world"])
        assert args == ["hello", "world"]
        assert kwargs == {}

    def test_flags(self):
        args, kwargs = _parse_args(["--tag", "python", "--title", "T"])
        assert args == []
        assert kwargs["tag"] == "python"
        assert kwargs["title"] == "T"

    def test_bool_flag(self):
        args, kwargs = _parse_args(["--fuzzy"])
        assert kwargs["fuzzy"] is True

    def test_equals(self):
        args, kwargs = _parse_args(["--lang=python"])
        assert kwargs["lang"] == "python"
        assert kwargs.get("language") is None

    def test_mixed(self):
        args, kwargs = _parse_args(["foo", "--limit", "5", "--fuzzy"])
        assert args == ["foo"]
        assert kwargs["limit"] == "5"
        assert kwargs["fuzzy"] is True

    def test_quoted_string(self):
        args, kwargs = _parse_args(["add", "'hello world'", "--title", "T"])
        assert args == ["add", "'hello world'"]
        assert kwargs["title"] == "T"


class TestCommandRegistry:
    def setup_method(self):
        self.registry = CommandRegistry()

    def test_known_commands_exist(self):
        assert "add" in self.registry.commands
        assert "list" in self.registry.commands
        assert "search" in self.registry.commands

    def test_aliases(self):
        assert self.registry.commands["ls"] is self.registry.commands["list"]
        assert self.registry.commands["a"] is self.registry.commands["add"]

    def test_unknown_command(self):
        result = self.registry.execute("nonexistent")
        assert result["type"] == "error"

    def test_empty_input(self):
        assert self.registry.execute("") is None

    def test_whitespace(self):
        assert self.registry.execute("   ") is None


class TestCommandsHeadless:
    def setup_method(self):
        self.registry = CommandRegistry()

    def test_stats_empty(self, tmp_path):
        import os

        old_env = os.environ.copy()
        env_updates = {
            "SNIPCONTEXT_STORAGE__DATA_DIR": str(tmp_path),
            "SNIPCONTEXT_STORAGE__SNIPPETS_DIR": "snippets",
            "SNIPCONTEXT_STORAGE__INDEX_DIR": "index",
        }
        os.environ.update(env_updates)
        try:
            result = self.registry.execute("stats")
        finally:
            os.environ.clear()
            os.environ.update(old_env)
        assert result["type"] == "message"
        assert "No snippets" in result["message"]

    def test_add_and_list(self, tmp_path):
        env_updates = {
            "SNIPCONTEXT_STORAGE__DATA_DIR": str(tmp_path),
            "SNIPCONTEXT_STORAGE__SNIPPETS_DIR": "snippets",
            "SNIPCONTEXT_STORAGE__INDEX_DIR": "index",
        }
        import os

        old_env = os.environ.copy()
        os.environ.update(env_updates)
        try:
            add_result = self.registry.execute("add 'print(1)' --title One --tag python")
            assert add_result["type"] == "snippet"
            list_result = self.registry.execute("list")
            assert list_result["type"] == "snippet_list"
            assert len(list_result["items"]) >= 1
        finally:
            os.environ.clear()
            os.environ.update(old_env)
