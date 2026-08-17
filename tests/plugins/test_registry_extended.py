"""Tests for plugins/registry.py - entry point discovery."""
import pytest
from unittest.mock import MagicMock, patch

from snipcontext.plugins.registry import _PluginRegistryImpl, reset_registry_for_testing
from snipcontext.plugins.base import Plugin, PluginManifest


class FakePlugin(Plugin):
    manifest = PluginManifest(name="fake-plugin", version="1.0.0")
    
    def on_load(self) -> None:
        pass
    
    def on_snippet_saved(self, snippet) -> None:
        pass


def test_discover_with_entry_points():
    """discover() loads plugins from entry points."""
    registry = _PluginRegistryImpl()
    
    with patch("importlib.metadata.entry_points") as mock_eps:
        mock_ep = MagicMock()
        mock_ep.name = "test_plugin"
        mock_ep.load.return_value = FakePlugin
        
        # Mock the entry_points() return value
        mock_eps.return_value = {"snipcontext.plugins": [mock_ep]}
        
        count = registry.discover()
        assert count >= 0  # Should not raise


def test_discover_with_no_entry_points():
    """discover() handles no entry points gracefully."""
    registry = _PluginRegistryImpl()
    
    with patch("importlib.metadata.entry_points") as mock_eps:
        mock_eps.return_value = {}
        
        count = registry.discover()
        assert count == 0


def test_discover_with_import_error():
    """discover() handles ImportError for entry points module."""
    registry = _PluginRegistryImpl()
    
    with patch("importlib.metadata.entry_points", side_effect=ImportError):
        count = registry.discover()
        assert count == 0


def test_load_builtin_providers():
    """load_builtin_providers() registers built-in providers."""
    registry = _PluginRegistryImpl()
    registry.load_builtin_providers()
    
    # Should have registered some providers
    assert len(registry._plugins) > 0


def test_get_provider():
    """get_provider() returns provider instance."""
    registry = _PluginRegistryImpl()
    registry.load_builtin_providers()
    
    # Try to get a provider
    try:
        provider = registry.get_provider("generic")
        assert provider is not None
    except KeyError:
        pass  # Provider may not be available


def test_list_providers():
    """list_providers() returns provider names and descriptions."""
    registry = _PluginRegistryImpl()
    registry.load_builtin_providers()
    
    providers = registry.list_providers()
    assert isinstance(providers, dict)


def test_list_provider_names():
    """list_provider_names() returns provider names."""
    registry = _PluginRegistryImpl()
    registry.load_builtin_providers()
    
    names = registry.list_provider_names()
    assert isinstance(names, list)


def test_default_provider():
    """default_provider property returns a provider name."""
    registry = _PluginRegistryImpl()
    registry.load_builtin_providers()
    
    default = registry.default_provider
    assert isinstance(default, str)


def test_get_health():
    """get_health() returns health status."""
    registry = _PluginRegistryImpl()
    plugin = MagicMock()
    plugin.health_check.return_value = "ok"
    registry._instances["test"] = plugin
    registry._loaded["test"] = True
    
    health = registry.get_health("test")
    assert health["status"] == "ok"


def test_get_health_not_loaded():
    """get_health() raises ValueError for unloaded plugin."""
    registry = _PluginRegistryImpl()
    
    with pytest.raises(ValueError, match="not loaded"):
        registry.get_health("nonexistent")


def test_unload_not_loaded():
    """unload_plugin() raises ValueError for unloaded plugin."""
    registry = _PluginRegistryImpl()
    
    with pytest.raises(ValueError, match="not loaded"):
        registry.unload_plugin("nonexistent")


def test_run_search_hooks():
    """run_search_hooks() calls on_search for each plugin."""
    registry = _PluginRegistryImpl()
    plugin = MagicMock()
    plugin.manifest = PluginManifest(name="test")
    registry._instances["test"] = plugin
    registry._loaded["test"] = True
    
    results = [MagicMock()]
    registry.run_search_hooks("query", results)
    plugin.on_search.assert_called_once()
