"""Golden/snapshot tests for CLI output."""

from __future__ import annotations

import os
import re

# Force Rich/table output to ASCII so snapshots are stable across environments.
# These env vars MUST be set before any Rich console is initialized.
os.environ.setdefault("TERM", "dumb")
os.environ.setdefault("NO_COLOR", "1")
os.environ.setdefault("FORCE_COLOR", "0")
os.environ.setdefault("RICH_TERMINAL", "ascii")
os.environ.setdefault("COLUMNS", "120")

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner

from snipcontext.cli.app import app

runner = CliRunner()


def _env(temp_dir: Path) -> dict[str, str]:
    return {
        "SNIPCONTEXT_STORAGE__DATA_DIR": str(temp_dir),
        "SNIPCONTEXT_STORAGE__SNIPPETS_DIR": "snippets",
        "SNIPCONTEXT_STORAGE__INDEX_DIR": "index",
        "COLUMNS": "120",
        "TERM": "dumb",
        "NO_COLOR": "1",
        "FORCE_COLOR": "0",
        "RICH_TERMINAL": "ascii",
        "RICH_TERMINAL_WIDTH": "120",
    }


def _invoke(temp_dir: Path, args: list[str], **kwargs):
    return runner.invoke(app, args, env=_env(temp_dir), **kwargs)


BOX_TRANSLATION = str.maketrans(
    {
        "┏": "+",
        "┳": "+",
        "┓": "+",
        "┡": "+",
        "┇": "+",
        "┩": "+",
        "┃": "|",
        "━": "-",
        "┉": "-",
        "┋": "-",
        "─": "-",
        "┌": "+",
        "┬": "+",
        "┐": "+",
        "├": "+",
        "┼": "+",
        "┤": "+",
        "└": "+",
        "┴": "+",
        "┘": "+",
        "│": "|",
        "╭": "+",
        "╮": "+",
        "╰": "+",
        "╯": "+",
        "╱": "-",
        "╲": "-",
    }
)


def _normalize(output: str, temp_dir: Path) -> str:
    # Replace temp path
    output = output.replace(str(temp_dir), "<tmp>")

    # Blast the entire Storage section with a fixed template so terminal
    # width differences between environments cannot affect snapshots.
    pattern = r"(Storage:)(.*?)(\n\n|\n[+\-].*$|\Z)"

    def _repl(match: re.Match[str]) -> str:
        return "Storage:\n  Data directory: <tmp>\n"

    output = re.sub(pattern, _repl, output, flags=re.DOTALL)

    # Normalize padding/whitespace for snapshot stability.
    output = "\n".join(line.rstrip() for line in output.splitlines())
    # Force ASCII table borders in case RICH_TERMINAL injection is late.
    return output.translate(BOX_TRANSLATION)


@pytest.fixture(autouse=True)
def _reset_registry():
    from snipcontext.plugins.registry import PluginRegistry

    PluginRegistry._instance = None
    yield
    PluginRegistry._instance = None


@pytest.fixture(autouse=True)
def _fixed_ids(mocker):

    fake_uuid = MagicMock(side_effect=["f" + str(i).zfill(21) for i in range(100)])
    mocker.patch("snipcontext.core.models.uuid.uuid4", fake_uuid)


def test_sc_list_empty(snapshot, tmp_path: Path):
    result = _invoke(tmp_path, ["list"])
    assert result.exit_code == 0, result.output
    snapshot.assert_match(result.output, "test_sc_list_empty")


def test_sc_list_with_snippets(snapshot, tmp_path: Path, mock_embeddings):
    _invoke(
        tmp_path,
        [
            "add",
            "def factorial(n):\n    return 1 if n <= 1 else n * factorial(n - 1)",
            "--title",
            "Factorial Function",
            "--lang",
            "python",
            "--tag",
            "python",
            "--tag",
            "recursion",
        ],
    )
    _invoke(
        tmp_path,
        [
            "add",
            "const debounce = (fn, ms) => {\n  let timer;\n  return (...args) => {\n    clearTimeout(timer);\n    timer = setTimeout(() => fn(...args), ms);\n  };\n};",
            "--title",
            "Debounce Function",
            "--lang",
            "javascript",
            "--tag",
            "javascript",
        ],
    )

    result = _invoke(tmp_path, ["list"])
    assert result.exit_code == 0, result.output
    snapshot.assert_match(_normalize(result.output, tmp_path), "test_sc_list_with_snippets")


def test_sc_export_claude(snapshot, tmp_path: Path, mock_embeddings):
    _invoke(
        tmp_path,
        [
            "add",
            "def hello(): pass",
            "--title",
            "Hello",
            "--lang",
            "python",
        ],
    )

    result = _invoke(tmp_path, ["export", "--provider", "claude", "--output", "-"])
    assert result.exit_code == 0, result.output
    snapshot.assert_match(result.output, "test_sc_export_claude")


def test_sc_export_openai(snapshot, tmp_path: Path, mock_embeddings):
    _invoke(
        tmp_path,
        [
            "add",
            "x = 42",
            "--title",
            "Answer",
            "--lang",
            "python",
        ],
    )

    result = _invoke(tmp_path, ["export", "--provider", "openai", "--output", "-"])
    assert result.exit_code == 0, result.output
    snapshot.assert_match(result.output, "test_sc_export_openai")


def test_sc_export_generic(snapshot, tmp_path: Path, mock_embeddings):
    _invoke(
        tmp_path,
        [
            "add",
            "x = 42",
            "--title",
            "Answer",
            "--lang",
            "python",
        ],
    )

    result = _invoke(tmp_path, ["export", "--provider", "generic", "--output", "-"])
    assert result.exit_code == 0, result.output
    snapshot.assert_match(result.output, "test_sc_export_generic")


def test_sc_stats(snapshot, tmp_path: Path, mock_embeddings):
    _invoke(
        tmp_path,
        [
            "add",
            "def factorial(n):\n    return 1 if n <= 1 else n * factorial(n - 1)",
            "--title",
            "Factorial",
            "--lang",
            "python",
            "--tag",
            "math",
        ],
    )
    _invoke(
        tmp_path,
        [
            "add",
            "const add = (a, b) => a + b;",
            "--title",
            "Add Function",
            "--lang",
            "javascript",
            "--tag",
            "math",
        ],
    )

    result = _invoke(tmp_path, ["stats"])
    assert result.exit_code == 0, result.output
    snapshot.assert_match(_normalize(result.output, tmp_path), "test_sc_stats")


def test_sc_list_unicode(snapshot, tmp_path: Path, mock_embeddings):
    _invoke(
        tmp_path,
        [
            "add",
            "// 你好 🚀\nconsole.log('émoji');",
            "--title",
            "Unicode Test 你好 🚀",
            "--lang",
            "javascript",
        ],
    )

    result = _invoke(tmp_path, ["list"])
    assert result.exit_code == 0, result.output
    snapshot.assert_match(_normalize(result.output, tmp_path), "test_sc_list_unicode")


def test_sc_list_special_chars(snapshot, tmp_path: Path, mock_embeddings):
    _invoke(
        tmp_path,
        [
            "add",
            "x = \"hello\\nworld\"\ny = 'foo\\tbar'",
            "--title",
            'Special <Chars> & "Quotes"',
            "--lang",
            "python",
        ],
    )

    result = _invoke(tmp_path, ["list"])
    assert result.exit_code == 0, result.output
    snapshot.assert_match(_normalize(result.output, tmp_path), "test_sc_list_special_chars")
