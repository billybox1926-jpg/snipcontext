"""Headless tests for the TUI app loop."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

pytest.importorskip("prompt_toolkit", reason="prompt_toolkit required for TUI tests")
from snipcontext.cli.context import reset_context  # noqa: E402
from snipcontext.tui.app import _print_help, _print_welcome, run  # noqa: E402


@pytest.fixture(autouse=True)
def _reset() -> None:
    reset_context()


def test_print_welcome(capsys):
    _print_welcome()
    output = capsys.readouterr().out
    assert "Interactive Shell" in output


def test_print_help(capsys):
    _print_help()
    output = capsys.readouterr().out
    assert "Available Commands" in output


def test_repl_exit():
    fake_session = MagicMock()
    fake_session.prompt.side_effect = ["exit"]
    with patch("snipcontext.tui.app.PromptSession", return_value=fake_session):
        assert run() == 0


def test_repl_help_then_exit():
    fake_session = MagicMock()
    fake_session.prompt.side_effect = ["help", "exit"]
    with patch("snipcontext.tui.app.PromptSession", return_value=fake_session):
        assert run() == 0


def test_repl_ctrl_d():
    fake_session = MagicMock()
    fake_session.prompt.side_effect = EOFError
    with patch("snipcontext.tui.app.PromptSession", return_value=fake_session):
        assert run() == 0
