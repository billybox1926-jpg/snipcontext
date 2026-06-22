"""Textual-based TUI for SnipContext."""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.widgets import Static


class SnippetBrowser(App[None]):
    """Minimal Textual browser scaffold."""

    CSS = """
    Screen {
        layout: vertical;
    }
    #main {
        height: 1fr;
    }
    #left {
        width: 30;
    }
    #right {
        width: 1fr;
    }
    #preview {
        height: 30%;
    }
    """

    def compose(self) -> ComposeResult:
        with Horizontal(id="main"):
            yield Static("Search / filter", id="left")
            yield Static("Snippet list", id="right")
        yield Static("Preview", id="preview")


def run_tui() -> int:
    app = SnippetBrowser()
    app.run()
    return 0
