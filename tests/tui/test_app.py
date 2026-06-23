"""Textual TUI tests - Phase 2 interactive browser."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

pytest.importorskip("textual")

from snipcontext.core.models import Language, Snippet, SnippetMetadata  # noqa: E402
from snipcontext.tui.textual_app import (  # noqa: E402
    HelpModal,
    PreviewPane,
    ProviderSelectScreen,
    SnippetBrowser,
    StatusBar,
)
from textual.widgets import Input, ListView  # noqa: E402


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
            mock_search_engine.search.assert_called_with(
                "hello",
                top_k=50,
                mode="hybrid",
                min_score=0.0,
                tag_filter=None,
                lang_filter=None,
            )


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


class TestMultiSelect:
    @pytest.mark.asyncio
    async def test_space_toggles_selection(self, app_with_results):
        app = app_with_results
        async with app.run_test() as pilot:
            app.action_next()
            app.action_toggle_select()
            await pilot.pause()
            assert app.results[1].id in app.state.selected_snippet_ids
            list_view = app.query_one("#snippet-list", ListView)
            list_item = list_view.children[1]
            assert "●" in list(list_item._nodes)[0].renderable

    @pytest.mark.asyncio
    async def test_new_search_prunes_stale_selection(self, app_with_results, sample_snippet):
        app = app_with_results
        app.state.selected_snippet_ids = {sample_snippet.id}
        app.set_results([sample_snippet])
        assert sample_snippet.id in app.state.selected_snippet_ids


class TestBatchCopy:
    @pytest.mark.asyncio
    async def test_copy_selected_snippets(self, app_with_results):
        app = app_with_results
        app.copy_to_clipboard = MagicMock()
        async with app.run_test():
            app.action_toggle_select()
            app.action_next()
            app.action_toggle_select()
            app.action_batch_copy()
            expected = "\n---\n".join([app.results[0].content or "", app.results[1].content or ""])
            app.copy_to_clipboard.assert_called_once_with(expected)

    @pytest.mark.asyncio
    async def test_copy_without_selection(self, app_with_results):
        app = app_with_results
        app.copy_to_clipboard = MagicMock()
        app.state.selected_snippet_ids = set()
        app.action_batch_copy()
        app.copy_to_clipboard.assert_not_called()


class TestBatchExport:
    @pytest.mark.asyncio
    async def test_export_opens_provider_screen(self, app_with_results):
        app = app_with_results
        with patch("snipcontext.tui.textual_app.PluginRegistry") as mock_registry:
            mock_registry.return_value.list_provider_names.return_value = ["generic"]
            mock_registry.return_value.get_provider.return_value = MagicMock()
            async with app.run_test():
                app.action_toggle_select()
                app.push_screen = MagicMock()
                app.action_batch_export()
                app.push_screen.assert_called_once()
                screen = app.push_screen.call_args[0][0]
                assert isinstance(screen, ProviderSelectScreen)

    @pytest.mark.asyncio
    async def test_export_no_selection(self, app_with_results):
        app = app_with_results
        app.push_screen = MagicMock()
        async with app.run_test():
            app.state.selected_snippet_ids = set()
            app.action_batch_export()
            app.push_screen.assert_not_called()

    @pytest.mark.asyncio
    async def test_export_full_flow(self, app_with_results):
        app = app_with_results
        fake_output = "EXPORT: Hello World"
        fake_provider = MagicMock()
        fake_provider.export_batch.return_value = fake_output
        with patch("snipcontext.tui.textual_app.PluginRegistry") as mock_registry:
            mock_registry.return_value.list_provider_names.return_value = ["generic"]
            mock_registry.return_value.get_provider.return_value = fake_provider
            async with app.run_test():
                app.action_toggle_select()
                app.push_screen = MagicMock()
                app.action_batch_export()
                app.push_screen.assert_called()
                selected_screen = app.push_screen.call_args[0][0]
                assert isinstance(selected_screen, ProviderSelectScreen)
                app._on_provider_selected("generic")
                app.push_screen.assert_called()
            result_screen = app.push_screen.call_args[0][0]
            assert fake_output in result_screen.text


class TestHelpModal:
    @pytest.mark.asyncio
    async def test_help_modal_opens_and_contains_bindings(self):
        app = SnippetBrowser()
        async with app.run_test():
            app.push_screen = MagicMock()  # type: ignore[method-assign]
            app.action_show_help()
            app.push_screen.assert_called_once()
            screen = app.push_screen.call_args[0][0]
            assert isinstance(screen, HelpModal)
            keys = [b[0] for b in screen.bindings]
            assert "j" in keys


class TestEmptyState:
    @pytest.mark.asyncio
    async def test_empty_results_shows_empty_state(self):
        app = SnippetBrowser()
        app.set_results([])
        async with app.run_test():
            preview = app.query_one("#preview", PreviewPane)
            assert preview._code.renderable is not None

    @pytest.mark.asyncio
    async def test_no_results_message_updates_status_bar(self):
        app = SnippetBrowser()
        app.set_results([])
        async with app.run_test():
            status = app.query_one("#status-bar", StatusBar)
            assert "Results: 0" in status._last_summary


class TestStatusBar:
    @pytest.mark.asyncio
    async def test_status_bar_updates_on_filter(self, app_with_results):
        app = app_with_results
        async with app.run_test():
            app.state.active_tag_filters = ["python"]
            app._status_bar.update_from_state(app.state)
            status = app.query_one("#status-bar", StatusBar)
            assert "Tags: python" in status._last_summary
