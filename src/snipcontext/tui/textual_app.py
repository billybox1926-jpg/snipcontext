"""Textual TUI for SnipContext - Phase 3."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from textual.app import App, ComposeResult
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    Checkbox,
    Footer,
    Header,
    Input,
    ListItem,
    ListView,
    Markdown,
    Select,
    Static,
)

from snipcontext.core.models import SearchResult, Snippet
from snipcontext.plugins.registry import PluginRegistry


@dataclass
class TuiState:
    query: str = ""
    active_tag_filters: list[str] = field(default_factory=list)
    active_language_filter: str | None = None
    min_score: float = 0.0
    selected_snippet_ids: set[str] = field(default_factory=set)
    results: list[Snippet] = field(default_factory=list)
    mode: Literal["browse", "filter"] = "browse"


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
    """Preview pane showing selected snippet details with loading state."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._code = Static("No snippet selected", id="preview-code")
        self._meta = Static("", id="preview-meta")
        self._loading = Static("", id="preview-loading")

    def compose(self) -> ComposeResult:
        yield self._loading
        yield self._code
        yield self._meta

    def set_loading(self, loading: bool) -> None:
        self._loading.update("Searching..." if loading else "")

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


class StatusBar(Static):
    """Reactive status bar summarising current UI state."""

    def __init__(self) -> None:
        super().__init__(id="status-bar")
        self._last_summary = ""

    def update_from_state(self, state: TuiState) -> None:
        parts = [
            f"Query: {state.query or '(none)'}",
            f"Results: {len(state.results)}",
        ]
        if state.active_tag_filters:
            parts.append(f"Tags: {', '.join(state.active_tag_filters)}")
        if state.active_language_filter:
            parts.append(f"Language: {state.active_language_filter}")
        if state.min_score:
            parts.append(f"Min score: {state.min_score:.2f}")
        if state.selected_snippet_ids:
            parts.append(f"Selected: {len(state.selected_snippet_ids)}")
        summary = " | ".join(parts)
        if summary != self._last_summary:
            self.update(summary)
            self._last_summary = summary


class FilterPanel(Vertical):
    """Collapsible filter panel."""

    def __init__(self, browser: SnippetBrowser, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.browser = browser
        self._all_tags: list[str] = []

    def compose(self) -> ComposeResult:
        yield Input(placeholder="Filter tags...", id="fp-tag-search")
        yield Vertical(id="fp-tag-list")
        yield Select([], id="fp-language-select", prompt="All languages")
        yield Input(type="number", id="fp-min-score", value="0")
        yield Static("Min score: 0.0", id="fp-min-score-label")

    def set_options(self, tags: list[str], languages: list[str]) -> None:
        if not self.is_mounted:
            return
        self._all_tags = sorted(set(tags))
        tag_list = self.query_one("#fp-tag-list", Vertical)
        tag_list.remove_children()
        for tag in self._all_tags:
            tag_list.append(  # type: ignore[attr-defined]
                Checkbox(
                    tag,
                    value=tag in self.browser.state.active_tag_filters,
                    name=tag,
                )
            )
        select = self.query_one(Select)
        select.set_options([("All", None)] + [(lang, lang) for lang in languages])
        current = self.browser.state.active_language_filter
        if current in languages:
            select.value = current
        else:
            select.value = None

    def _on_tag_search_changed(self, event: Input.Changed) -> None:
        query = event.value.strip().lower()
        tag_list = self.query_one("#fp-tag-list", Vertical)
        if not query:
            tags_to_show = self._all_tags
        else:
            try:
                from rapidfuzz import fuzz, process

                scored = process.extract(
                    query,
                    self._all_tags,
                    scorer=fuzz.token_set_ratio,
                    score_cutoff=60,
                )
                tags_to_show = [match for match, score, _ in scored]
            except ImportError:
                tags_to_show = [t for t in self._all_tags if query in t.lower()]
        tag_list.remove_children()
        for tag in tags_to_show:
            tag_list.append(  # type: ignore[attr-defined]
                Checkbox(
                    tag,
                    value=tag in self.browser.state.active_tag_filters,
                    name=tag,
                )
            )

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        tag = event.checkbox.name or ""
        active = self.browser.state.active_tag_filters
        if event.checkbox.value:
            if tag not in active:
                active.append(tag)
        else:
            self.browser.state.active_tag_filters = [t for t in active if t != tag]
        self.browser.set_timer(0.1, self.browser._do_search)

    def on_select_changed(self, event: Select.Changed) -> None:
        self.browser.state.active_language_filter = event.value or None  # type: ignore[assignment]
        self.browser.set_timer(0.1, self.browser._do_search)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "fp-min-score":
            try:
                value = float(event.value)
            except ValueError:
                value = 0.0
            value = max(0.0, min(1.0, value))
            self.browser.state.min_score = value
            label = self.query_one("#fp-min-score-label", Static)
            label.update(f"Min score: {value:.1f}")
            self.browser.set_timer(0.1, self.browser._do_search)


class HelpModal(ModalScreen[None]):
    """Keybinding reference modal."""

    BINDINGS = [("escape", "dismiss", "Close")]

    def __init__(self, bindings: list) -> None:
        super().__init__()
        self.bindings = bindings

    def compose(self) -> ComposeResult:
        rows = "\n".join(f"| `{key}` | {action} |" for key, action, _ in self.bindings)
        md = f"# Keybindings\n\n| Key | Action |\n| --- | --- |\n{rows}"
        yield Markdown(md)
        yield Button("Close", id="help-close")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "help-close":
            self.dismiss()


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
    FilterPanel {
        width: 25;
        dock: right;
        padding: 1;
    }
    PreviewPane {
        height: 1fr;
        padding: 1;
    }
    #preview-code {
        height: 1fr;
        overflow: auto;
    }
    #preview-loading {
        dock: top;
        height: 1;
        content-align: center middle;
        text-style: bold;
        color: $primary;
    }
    #status-bar {
        dock: bottom;
        height: 1;
        padding: 0 1;
        text-align: left;
        content-align: left middle;
        background: $panel;
        color: $text;
    }
    .selected {
        text-style: bold;
        color: $primary;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("j", "action_next", "Next"),
        ("k", "action_prev", "Previous"),
        ("enter", "copy", "Copy"),
        ("ctrl+f", "toggle_filter", "Filter"),
        ("space", "toggle_select", "Select"),
        ("ctrl+y", "batch_copy", "Copy Selected"),
        ("ctrl+e", "batch_export", "Export Selected"),
        ("?", "show_help", "Help"),
    ]

    def __init__(self, search_engine=None, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.search_engine = search_engine
        self.results: list[Snippet] = []
        self.cursor_index: int = 0
        self.query: str = ""  # type: ignore[assignment]
        self.state = TuiState()
        self._status_bar = StatusBar()

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="main"):
            yield SearchPanel()
            yield SnippetList(id="snippet-list")
            yield FilterPanel(self, id="filter-panel")
        yield PreviewPane(id="preview")
        yield self._status_bar
        yield Footer()

    def on_mount(self) -> None:
        self._load_snippets()
        self._status_bar.update_from_state(self.state)

    def set_results(self, results: list[Snippet]) -> None:
        self.results = results
        self.state.results = results
        valid_ids = {snippet.id for snippet in results}
        self.state.selected_snippet_ids = {
            sid for sid in self.state.selected_snippet_ids if sid in valid_ids
        }
        self.cursor_index = 0
        if self.is_running:
            self._render_list()
            self._sync_filter_options()
            self._status_bar.update_from_state(self.state)

    def _load_snippets(self) -> None:
        # Placeholder: in a real app this would read from storage
        if not self.results:
            self.results = []
            self._render_list()
        if self.is_running:
            self._render_list()
            self._status_bar.update_from_state(self.state)

    def _render_list(self) -> None:
        list_view = self.query_one("#snippet-list", SnippetList)
        list_view.remove_children()
        for snippet in self.results:
            marker = "● " if snippet.id in self.state.selected_snippet_ids else "○ "
            list_view.append(ListItem(Static(marker + snippet.metadata.title)))
        if self.results:
            self.cursor_index = min(self.cursor_index, len(self.results) - 1)
            list_view.index = self.cursor_index
            self._update_preview()
        else:
            self.query_one("#preview", PreviewPane).set_snippet(None)

    def _update_preview(self) -> None:
        preview = self.query_one("#preview", PreviewPane)
        if 0 <= self.cursor_index < len(self.results):
            preview.set_snippet(self.results[self.cursor_index])
        else:
            preview.set_snippet(None)

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "search-input":
            self.query = event.value
            self.query_one("#preview", PreviewPane).set_loading(True)
            self.set_timer(0.3, self._do_search)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "search-button":
            self.query_one("#preview", PreviewPane).set_loading(True)
            self._do_search()

    def _do_search(self) -> None:
        query = self.query
        self.state.query = query
        self.state.results = self._search_adapter(query)
        self.results = self.state.results
        self.cursor_index = 0
        self._render_list()
        self._sync_filter_options()
        self.query_one("#preview", PreviewPane).set_loading(False)
        self._status_bar.update_from_state(self.state)

    def _search_adapter(self, query: str) -> list[Snippet]:
        if not self.search_engine:
            return []
        try:
            raw = self.search_engine.search(
                query,
                top_k=50,
                mode="hybrid",
                min_score=self.state.min_score,
                tag_filter=self.state.active_tag_filters or None,
                lang_filter=[self.state.active_language_filter]
                if self.state.active_language_filter
                else None,
            )
        except TypeError:
            raw = self.search_engine.search(query)  # type: ignore[call-arg]

        if raw and isinstance(raw[0], SearchResult):
            snippets = [item.snippet for item in raw]
        else:
            snippets = list(raw)

        tag_set = {tag.lower() for tag in self.state.active_tag_filters}
        lang = self.state.active_language_filter
        filtered: list[Snippet] = []
        for snippet in snippets:
            if tag_set and not tag_set.issubset({tag.lower() for tag in snippet.tags}):
                continue
            if lang and snippet.metadata.language.value != lang:
                continue
            filtered.append(snippet)
        return filtered

    def action_next(self) -> None:
        if self.results and self.cursor_index < len(self.results) - 1:
            self.cursor_index += 1
            self.query_one("#snippet-list", SnippetList).index = self.cursor_index
            self._update_preview()
            self._status_bar.update_from_state(self.state)

    def action_prev(self) -> None:
        if self.results and self.cursor_index > 0:
            self.cursor_index -= 1
            self.query_one("#snippet-list", SnippetList).index = self.cursor_index
            self._update_preview()
            self._status_bar.update_from_state(self.state)

    def action_copy(self) -> None:
        if 0 <= self.cursor_index < len(self.results):
            snippet = self.results[self.cursor_index]
            text = snippet.content or snippet.encrypted_content or ""
            try:
                self.copy_to_clipboard(text)
                self.notify(f"Copied snippet '{snippet.metadata.title}' to clipboard")
            except Exception:
                self.notify("Clipboard unavailable", severity="warning")

    def action_toggle_select(self) -> None:
        if not self.results:
            return
        snippet = self.results[self.cursor_index]
        if snippet.id in self.state.selected_snippet_ids:
            self.state.selected_snippet_ids.discard(snippet.id)
        else:
            self.state.selected_snippet_ids.add(snippet.id)
        self._render_list()
        self._status_bar.update_from_state(self.state)

    def action_batch_copy(self) -> None:
        selected = [s for s in self.results if s.id in self.state.selected_snippet_ids]
        if not selected:
            self.notify("No snippets selected")
            return
        joined = "\n---\n".join(s.content or s.encrypted_content or "" for s in selected)
        try:
            self.copy_to_clipboard(joined)
            self.notify(f"Copied {len(selected)} snippets")
        except Exception:
            self.notify("Clipboard unavailable", severity="warning")

    def action_batch_export(self) -> None:
        selected = [s for s in self.results if s.id in self.state.selected_snippet_ids]
        if not selected:
            self.notify("No snippets selected")
            return
        try:
            names = list(PluginRegistry().list_provider_names())
        except Exception as exc:
            self.notify(f"Failed to load providers: {exc}", severity="error")
            return
        if not names:
            self.notify("No providers available", severity="warning")
            return
        self.push_screen(ProviderSelectScreen(names), self._on_provider_selected)

    def _on_provider_selected(self, provider_name: str | None) -> None:
        if not provider_name:
            return
        selected = [s for s in self.results if s.id in self.state.selected_snippet_ids]
        try:
            provider = PluginRegistry().get_provider(provider_name)
            output = provider.export_batch(selected)
            self.push_screen(ExportResultScreen(output))
        except Exception as exc:
            self.notify(f"Export failed: {exc}", severity="error")

    def action_toggle_filter(self) -> None:
        panel = self.query_one("#filter-panel", FilterPanel)
        current = panel.styles.display
        panel.styles.display = "none" if current != "none" else "block"

    def action_show_help(self) -> None:
        self.push_screen(HelpModal(self.BINDINGS))

    def _sync_filter_options(self) -> None:
        if not self.is_running:
            return
        if not hasattr(self, "filter_panel"):
            return
        tags = sorted({tag for snippet in self.results for tag in snippet.tags})
        langs = sorted({snippet.metadata.language.value for snippet in self.results})
        self.filter_panel.set_options(tags, langs)

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        if event.list_view.id == "snippet-list":
            self.cursor_index = event.list_view.index or 0
            self._update_preview()
            self._status_bar.update_from_state(self.state)


class ProviderSelectScreen(ModalScreen[str]):
    BINDINGS = [("escape", "dismiss", "Dismiss")]

    def __init__(self, providers: list[str], *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.providers = providers

    def compose(self) -> ComposeResult:
        yield Select(
            [(provider, provider) for provider in self.providers],
            id="provider-select",
            prompt="Choose a provider",
        )

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.value:
            self.dismiss(str(event.value))


class ExportResultScreen(ModalScreen[str]):
    BINDINGS = [("escape", "dismiss", "Close")]

    def __init__(self, text: str, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.text = text

    def compose(self) -> ComposeResult:
        with ScrollableContainer(id="export-result"):
            yield Static(self.text)


def run_tui() -> int:
    app = SnippetBrowser()
    app.run()
    return 0
