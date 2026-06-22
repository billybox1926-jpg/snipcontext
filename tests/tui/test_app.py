"""Headless tests for the TUI app loop."""

from __future__ import annotations

from unittest.mock import patch

import pytest

pytest.importorskip("prompt_toolkit", reason="prompt_toolkit required for TUI tests")
from snipcontext.cli.context import reset_context  # noqa: E402
from snipcontext.tui.textual_app import SnippetBrowser  # noqa: E402


@pytest.fixture(autouse=True)
def _reset() -> None:
    reset_context()


def test_snippet_browser_compose() -> None:
    app = SnippetBrowser()
    with patch.object(app, "push_screen"):
        app.run()
    assert app.query_one("#main") is not None
    assert app.query_one("#left") is not None
    assert app.query_one("#right") is not None
    assert app.query_one("#preview") is not None
