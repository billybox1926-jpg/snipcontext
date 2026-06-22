"""Textual TUI for SnipContext - Phase 2 Interactive Browser."""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Footer, Header, Input, ListItem, ListView, Static

from snipcontext.core.models import Snippet


class SearchPanel(Horizontal):
    """Search input with a submit button."""

    def compose(self) -> ComposeResult:
        yield Input(placeholder="Search snippets...", id="search-input")
        yield Button("Search", id="search-button")


class SnippetList(ListView):
    """Selectable snippet list."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.cursor_index = 0


class PreviewPane(Vertical):
    """Preview pane showing selected snippet details."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._code = Static("No snippet selected", id="preview-code")
        self._meta = Static("", id="preview-meta")

    def compose(self) -> ComposeResult:
        yield self._code
        yield self._meta

    def set_snippet(self, snippet: Snippet | None) -> None:
        if snippet is None:
            self._code.update("No snippet selected")
            self._meta.update("")
            return

        from rich.panel import Panel
        from rich.syntax import Syntax

        code = snippet.content or snippet.encrypted_content or ""
        lang = snippet.metadata.language.value
        if lang == "unknown":
            lang = "text"

        try:
            syntax = Syntax(
                code,
                lang,
                theme="monokai",
                line_numbers=False,
                word_wrap=True,
            )
            self._code.update(syntax)
        except Exception:
            self._code.update(code)

        meta_text = "\n".join(
            [
                f"Title: {snippet.metadata.title}",
                f"Language: {lang}",
                f"Tags: {', '.join(snippet.tags)}",
                f"Confidence: {getattr(snippet, 'confidence', 'N/A')}",
            ]
        )
        self._meta.update(Panel(meta_text, title="Metadata", border_style="blue"))


class SnippetBrowser(App[None]):
    """Interactive Textual browser for snippets."""

    CSS = """
    Screen {
        layout: vertical;
    }
    #main {
        height: 1fr;
    }
    SearchPanel {
        height: 3;
        padding: 0 1;
    }
    #search-input {
        width: 1fr;
    }
    #search-button {
        width: 10;
    }
    SnippetList {
        width: 30;
        dock: left;
    }
    PreviewPane {
        height: 1fr;
        padding: 1;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("j", "action_next", "Next"),
        ("k", "action_prev", "Previous"),
        ("enter", "copy", "Copy"),
    ]

    def __init__(self, search_engine=None, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.search_engine = search_engine
        self.results: list[Snippet] = []
        self.cursor_index: int = 0
        self.query: str = ""

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="main"):
            yield SearchPanel()
            yield SnippetList(id="snippet-list")
        yield PreviewPane(id="preview")
        yield Footer()

    def on_mount(self) -> None:
        self._load_snippets()

    def set_results(self, results: list[Snippet]) -> None:
        self.results = results
        self.cursor_index = 0
        if self.is_running:
            self._render_list()

    def _load_snippets(self) -> None:
        # Placeholder: in a real app this would read from storage
        if not self.results:
            self.results = []
            self._render_list()
        if self.is_running:
            self._render_list()

    def _render_list(self) -> None:
        list_view = self.query_one("#snippet-list", SnippetList)
        list_view.remove_children()
        for snippet in self.results:
            list_view.append(ListItem(Static(snippet.metadata.title)))
        if self.results:
            self.cursor_index = min(self.cursor_index, len(self.results) - 1)
            list_view.index = self.cursor_index
            self._update_preview()

    def _update_preview(self) -> None:
        preview = self.query_one("#preview", PreviewPane)
        if 0 <= self.cursor_index < len(self.results):
            preview.set_snippet(self.results[self.cursor_index])
        else:
            preview.set_snippet(None)

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "search-input":
            self.query = event.value
            self.set_timer(0.3, self._do_search)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "search-button":
            self._do_search()

    def _do_search(self) -> None:
        query = self.query
        if self.search_engine is not None:
            try:
                self.results = self.search_engine.search(query)
            except Exception:
                self.results = []
        else:
            # Placeholder: no search engine available
            self.results = []
        self.cursor_index = 0
        self._render_list()

    def action_next(self) -> None:
        if self.results and self.cursor_index < len(self.results) - 1:
            self.cursor_index += 1
            self.query_one("#snippet-list", SnippetList).index = self.cursor_index
            self._update_preview()

    def action_prev(self) -> None:
        if self.results and self.cursor_index > 0:
            self.cursor_index -= 1
            self.query_one("#snippet-list", SnippetList).index = self.cursor_index
            self._update_preview()

    def action_copy(self) -> None:
        if 0 <= self.cursor_index < len(self.results):
            snippet = self.results[self.cursor_index]
            text = snippet.content or snippet.encrypted_content or ""
            try:
                self.copy_to_clipboard(text)
                self.notify(f"Copied snippet '{snippet.metadata.title}' to clipboard")
            except Exception:
                pass

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        if event.list_view.id == "snippet-list":
            self.cursor_index = event.list_view.index
            self._update_preview()


def run_tui() -> int:
    app = SnippetBrowser()
    app.run()
    return 0
