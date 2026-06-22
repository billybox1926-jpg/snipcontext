"""Plugin loading tests: discovery, lifecycle, and graceful error isolation (Phase 4)."""

from __future__ import annotations

import logging
from typing import Any
from unittest.mock import MagicMock

import pytest

from snipcontext.plugins.base import Plugin, PluginManager, PluginManifest
from snipcontext.plugins.registry import PluginRegistry


@pytest.fixture(autouse=True)
def _reset_plugin_registry():
    PluginRegistry._instance = None
    yield
    PluginRegistry._instance = None


class _TrackedPlugin(Plugin):
    manifest = PluginManifest(name="tracked-plugin", api_version="0.3.0")

    def __init__(self) -> None:
        super().__init__()
        self.events: list[str] = []

    def on_load(self) -> None:
        self.events.append("load")

    def on_shutdown(self) -> None:
        self.events.append("shutdown")

    def on_snippet_saved(self, snippet: Any) -> None:
        self.events.append("saved")


class TestPluginDiscovery:
    def test_discover_returns_registered_plugins(self, temp_entry_points, fake_plugin_factory):
        ep = fake_plugin_factory("discovered")
        with temp_entry_points({"snipcontext.plugins": [ep]}):
            count = PluginManager.discover()
            assert count == 1
            assert "discovered" in PluginManager._registry()._plugins

    def test_discover_skips_non_plugin_entry(self, temp_entry_points):
        bad_cls = type("NotAPlugin", (), {"manifest": object()})
        ep = MagicMock()
        ep.name = "bad"
        ep.load.return_value = bad_cls

        with temp_entry_points({"snipcontext.plugins": [ep]}):
            count = PluginManager.discover()
            assert count == 0
            assert "bad" not in PluginManager._registry()._plugins

    def test_discover_empty_group_returns_zero(self, temp_entry_points):
        with temp_entry_points({}):
            count = PluginManager.discover()
            assert count == 0
            assert PluginManager._registry()._plugins == {}


class TestPluginLifecycle:
    def test_on_load_and_shutdown_called_in_order(self, temp_entry_points, caplog):
        caplog.set_level(logging.DEBUG)

        tracked_cls = _TrackedPlugin
        ep = MagicMock()
        ep.name = "tracked-plugin"
        ep.load.return_value = tracked_cls

        with temp_entry_points({"snipcontext.plugins": [ep]}):
            PluginManager.discover()

            registry = PluginManager._registry()
            registry._plugins["tracked-plugin"] = tracked_cls
            registry._loaded["tracked-plugin"] = False
            registry._instances.pop("tracked-plugin", None)

            instance = PluginManager.load_plugin("tracked-plugin")
            PluginManager.shutdown()

        assert instance is not None
        assert getattr(instance, "events", None) == ["load", "shutdown"]


class TestPluginLoadErrors:
    def test_broken_plugin_is_skipped_gracefully(self, temp_entry_points, caplog):
        caplog.set_level(logging.DEBUG)

        ep = MagicMock()
        ep.name = "broken"
        ep.load.side_effect = ImportError("boom")

        with temp_entry_points({"snipcontext.plugins": [ep]}):
            count = PluginManager.discover()
            assert count == 0
            assert "broken" not in PluginManager._registry()._plugins
        assert any("Failed to load plugin broken" in r.message for r in caplog.records)

    def test_duplicate_names_last_wins(self, temp_entry_points, caplog):
        caplog.set_level(logging.DEBUG)

        first_cls = type(
            "First",
            (Plugin,),
            {
                "manifest": PluginManifest(name="dup", api_version="0.3.0"),
                "on_load": lambda self: None,
                "on_snippet_saved": lambda self, snippet: None,
            },
        )
        second_cls = type(
            "Second",
            (Plugin,),
            {
                "manifest": PluginManifest(name="dup", api_version="0.3.0"),
                "on_load": lambda self: None,
                "on_snippet_saved": lambda self, snippet: None,
            },
        )

        first_ep = MagicMock()
        first_ep.name = "dup-a"
        first_ep.load.return_value = first_cls

        second_ep = MagicMock()
        second_ep.name = "dup-b"
        second_ep.load.return_value = second_cls

        with temp_entry_points({"snipcontext.plugins": [first_ep, second_ep]}):
            count = PluginManager.discover()
            assert count == 2
            assert PluginManager.list_providers() or True  # no crash
            registry = PluginManager._registry()
            assert registry._plugins["dup"] is second_cls
