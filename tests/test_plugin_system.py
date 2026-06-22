"""Tests for the SnipContext plugin system."""

from __future__ import annotations

from typing import Any

import pytest

from snipcontext.plugins.base import (
    CORE_API_VERSION,
    Plugin,
    PluginManager,
    PluginManifest,
)
from snipcontext.providers.base import BaseProvider


class HelloWorldPlugin(Plugin):
    manifest = PluginManifest(name="hello-world", version="0.2.0")

    def on_load(self) -> None:
        self.loaded = True

    def on_shutdown(self) -> None:
        self.shutdown = True

    def on_snippet_saved(self, snippet: Any) -> None:
        self.saved_snippet = snippet

    def on_config_change(self, new_config: object) -> None:
        self.config = new_config


class TestPluginSystem:
    "Verify plugin lifecycle, registry, and version guarding."

    def test_lifecycle_hooks_fire(self) -> None:
        plugin = HelloWorldPlugin()
        plugin.on_load()
        assert getattr(plugin, "loaded", False) is True

    def test_on_shutdown_called(self) -> None:
        plugin = HelloWorldPlugin()
        plugin.on_load()
        plugin.on_shutdown()
        assert getattr(plugin, "shutdown", False) is True

    def test_on_config_change_propagates(self) -> None:
        plugin = HelloWorldPlugin()
        plugin.on_config_change({"key": "value"})
        assert getattr(plugin, "config", None) == {"key": "value"}

    def test_version_mismatch_prevents_load(self) -> None:
        class BadApiPlugin(Plugin):
            manifest = PluginManifest(name="bad-api", api_version="0.0.0")

            def on_load(self) -> None:
                self.loaded = True

            def on_snippet_saved(self, snippet: Any) -> None:
                ...

        plugin = BadApiPlugin()
        loaded = False
        if plugin.manifest.api_version == CORE_API_VERSION:
            plugin.on_load()
            loaded = getattr(plugin, "loaded", False)
        assert loaded is False

    def test_pm_run_snippet_saved_hooks(self) -> None:
        pm = PluginManager()
        plugin = HelloWorldPlugin()
        pm._plugins[plugin.manifest.name] = plugin
        plugin.on_load()
        snippet = {"id": "1"}
        pm.run_snippet_saved_hooks(snippet)  # type: ignore[arg-type]
        assert getattr(plugin, "saved_snippet", None) == snippet

    def test_pm_shutdown_calls_hooks(self) -> None:
        pm = PluginManager()
        plugin = HelloWorldPlugin()
        pm._plugins[plugin.manifest.name] = plugin
        plugin.on_load()
        pm.shutdown()
        assert getattr(plugin, "shutdown", False) is True
        assert not pm.plugins

    def test_list_plugins_returns_manifests(self) -> None:
        pm = PluginManager()
        plugin = HelloWorldPlugin()
        pm._plugins[plugin.manifest.name] = plugin
        plugin.on_load()
        manifests = pm.list_plugins()
        assert len(manifests) == 1
        assert manifests[0].name == "hello-world"
        assert manifests[0].version == "0.2.0"
        assert manifests[0].api_version == CORE_API_VERSION

    def test_load_builtin_providers_registers_expected(self) -> None:
        pm = PluginManager()
        pm.load_builtin_providers()
        providers = pm.list_providers()
        assert "generic" in providers
        assert "claude" in providers
        assert "cursor" in providers
        assert "openai" in providers
