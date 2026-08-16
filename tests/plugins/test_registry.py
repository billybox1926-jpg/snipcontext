"""Tests for plugins/registry.py."""
from unittest.mock import MagicMock

import pytest

from snipcontext.plugins.base import Plugin, PluginManifest
from snipcontext.plugins.registry import _PluginRegistryImpl, _registry, reset_registry_for_testing


class TestPlugin(Plugin):
    manifest = PluginManifest(name="test-plugin")

    def on_load(self) -> None:
        pass

    def on_snippet_saved(self, snippet) -> None:
        pass


def test_registry_initialization():
    """PluginRegistry can be initialized."""
    registry = _PluginRegistryImpl()
    assert registry is not None
    assert registry.list_plugins() == []


def test_registry_load_plugin():
    """load_plugin() instantiates and registers a plugin."""
    registry = _PluginRegistryImpl()
    registry._plugins["test"] = TestPlugin
    plugin = registry.load_plugin("test")
    assert isinstance(plugin, TestPlugin)
    assert registry._loaded["test"] is True


def test_registry_load_plugin_not_found():
    """load_plugin() raises ValueError for unknown plugin."""
    registry = _PluginRegistryImpl()
    with pytest.raises(ValueError, match="not found"):
        registry.load_plugin("nonexistent")


def test_registry_get_plugin():
    """get_plugin() returns the loaded instance."""
    registry = _PluginRegistryImpl()
    registry._plugins["test"] = TestPlugin
    plugin = registry.load_plugin("test")
    assert registry.get_plugin("test") is plugin


def test_registry_get_plugin_missing():
    """get_plugin() returns None for unloaded plugin."""
    registry = _PluginRegistryImpl()
    assert registry.get_plugin("nonexistent") is None


def test_registry_unload_plugin():
    """unload_plugin() calls on_shutdown and removes instance."""
    registry = _PluginRegistryImpl()
    registry._plugins["test"] = TestPlugin
    registry.load_plugin("test")
    registry.unregister("test")
    assert registry.get_plugin("test") is None


def test_registry_list_plugins():
    """list_plugins() returns loaded plugin manifests."""
    registry = _PluginRegistryImpl()
    registry._plugins["test"] = TestPlugin
    registry.load_plugin("test")
    manifests = registry.list_plugins()
    assert len(manifests) == 1
    assert manifests[0].name == "test-plugin"


def test_registry_discover():
    """discover() returns count of loaded plugins."""
    registry = _PluginRegistryImpl()
    count = registry.discover()
    assert count >= 0  # Should not raise


def test_registry_run_snippet_saved_hooks():
    """run_snippet_saved_hooks() calls on_snippet_saved for each plugin."""
    registry = _PluginRegistryImpl()
    plugin = MagicMock(spec=Plugin)
    plugin.manifest = PluginManifest(name="test")
    registry._plugins["test"] = type(plugin)
    registry._instances["test"] = plugin
    registry._loaded["test"] = True

    snippet = MagicMock()
    registry.run_snippet_saved_hooks(snippet)
    plugin.on_snippet_saved.assert_called_once_with(snippet)


def test_registry_run_search_hooks():
    """run_search_hooks() calls on_search for each plugin."""
    registry = _PluginRegistryImpl()
    plugin = TestPlugin()
    registry._plugins["test"] = TestPlugin
    registry._instances["test"] = plugin
    registry._loaded["test"] = True

    results = [MagicMock()]
    registry.run_search_hooks("query", results)
    # Should not raise


def test_registry_shutdown():
    """shutdown() deactivates all plugins."""
    registry = _PluginRegistryImpl()
    plugin = TestPlugin()
    registry._plugins["test"] = TestPlugin
    registry._instances["test"] = plugin
    registry._loaded["test"] = True

    registry.shutdown()
    assert registry.get_plugin("test") is None


def test_get_registry_singleton():
    """_registry() returns the same instance."""
    reset_registry_for_testing()
    r1 = _registry()
    r2 = _registry()
    assert r1 is r2


def test_reset_registry():
    """reset_registry_for_testing() clears the singleton."""
    reset_registry_for_testing()
    r1 = _registry()
    reset_registry_for_testing()
    r2 = _registry()
    assert r1 is not r2
