"""Textual TUI tests - Phase 2 interactive browser."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

pytest.importorskip("textual")

from textual.widgets import Input  # noqa: E402

from snipcontext.core.models import Language, Snippet, SnippetMetadata  # noqa: E402
from snipcontext.tui.textual_app import PreviewPane, SnippetBrowser  # noqa: E402


@pytest.fixture
def sample_snippet():
    return Snippet(
        content="def hello():\n    print('world')",
        metadata=SnippetMetadata(
            title="Hello World",
            description="A simple hello world",
            language=Language.PYTHON,
        ),
        tags=["python", "example"],
    )


@pytest.fixture
def sample_snippet_2():
    return Snippet(
        content="const add = (a, b) => a + b;",
        metadata=SnippetMetadata(
            title="Add Function",
            description="Simple add function",
            language=Language.JAVASCRIPT,
        ),
        tags=["javascript", "math"],
    )


@pytest.fixture
def app_with_results(sample_snippet, sample_snippet_2):
    app = SnippetBrowser()
    app.set_results([sample_snippet, sample_snippet_2])
    return app


@pytest.fixture
def mock_search_engine():
    engine = MagicMock()
    engine.search = MagicMock(return_value=[])
    return engine


class TestSearchPanel:
    @pytest.mark.asyncio
    async def test_typing_updates_query(self, mock_search_engine):
        app = SnippetBrowser(search_engine=mock_search_engine)
        async with app.run_test():
            input_widget = app.query_one("#search-input", Input)
            input_widget.value = "auth"
            app.on_input_changed(Input.Changed(input_widget, value="auth"))
            assert app.query == "auth"

    @pytest.mark.asyncio
    async def test_search_button_calls_engine(self, mock_search_engine, sample_snippet):
        mock_search_engine.search.return_value = [sample_snippet]
        app = SnippetBrowser(search_engine=mock_search_engine)
        async with app.run_test():
            app.query = "hello"
            app._do_search()
            mock_search_engine.search.assert_called_with("hello")


class TestNavigation:
    @pytest.mark.asyncio
    async def test_j_moves_next(self, app_with_results):
        app = app_with_results
        async with app.run_test():
            app.action_next()
            assert app.cursor_index == 1

    @pytest.mark.asyncio
    async def test_k_moves_prev(self, app_with_results):
        app = app_with_results
        app.cursor_index = 1
        async with app.run_test():
            app.action_prev()
            assert app.cursor_index == 0

    @pytest.mark.asyncio
    async def test_preview_updates(self, app_with_results):
        app = app_with_results
        async with app.run_test():
            app.action_next()
            preview = app.query_one("#preview", PreviewPane)
            assert preview._code.renderable is not None


class TestCopyToClipboard:
    @pytest.mark.asyncio
    async def test_enter_copies_content(self, app_with_results):
        app = app_with_results
        app.copy_to_clipboard = MagicMock()
        async with app.run_test():
            app.action_copy()
            app.copy_to_clipboard.assert_called_once_with(app.results[0].content)
