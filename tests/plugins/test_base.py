"""Tests for plugins/base.py."""

from unittest.mock import MagicMock

import pytest

from snipcontext.plugins.base import Plugin, PluginManifest


class ConcretePlugin(Plugin):
    """A concrete plugin for testing."""

    manifest = PluginManifest(name="test-plugin", version="1.0.0")

    def on_load(self) -> None:
        self.loaded = True

    def on_snippet_saved(self, snippet) -> None:
        self.saved_snippet = snippet


def test_plugin_manifest_defaults():
    """PluginManifest initializes with correct defaults."""
    manifest = PluginManifest(name="test")
    assert manifest.name == "test"
    assert manifest.version == "0.1.0"
    assert manifest.api_version == "0.3.0"
    assert manifest.dependencies == {}
    assert manifest.requires == []
    assert manifest.description == ""
    assert manifest.author == ""


def test_plugin_manifest_custom_values():
    """PluginManifest accepts custom values."""
    manifest = PluginManifest(
        name="custom",
        version="2.0.0",
        dependencies={"numpy": ">=1.20"},
        requires=["faiss"],
        description="A test plugin",
        author="Test Author",
    )
    assert manifest.name == "custom"
    assert manifest.version == "2.0.0"
    assert manifest.dependencies == {"numpy": ">=1.20"}
    assert manifest.requires == ["faiss"]
    assert manifest.description == "A test plugin"
    assert manifest.author == "Test Author"


def test_plugin_initialization():
    """Plugin can be initialized and manifest is accessible."""
    plugin = ConcretePlugin()
    assert plugin.manifest.name == "test-plugin"
    assert plugin.manifest.version == "1.0.0"


def test_plugin_on_load():
    """on_load() is called to initialize the plugin."""
    plugin = ConcretePlugin()
    plugin.on_load()
    assert plugin.loaded is True


def test_plugin_on_snippet_saved():
    """on_snippet_saved() receives the saved snippet."""
    plugin = ConcretePlugin()
    snippet = MagicMock()
    plugin.on_snippet_saved(snippet)
    assert plugin.saved_snippet is snippet


def test_plugin_on_snippet_loaded_default():
    """on_snippet_loaded() has a default no-op implementation."""
    plugin = ConcretePlugin()
    snippet = MagicMock()
    # Should not raise
    plugin.on_snippet_loaded(snippet)


def test_plugin_on_search_default():
    """on_search() returns results unchanged by default."""
    plugin = ConcretePlugin()
    results = [MagicMock(), MagicMock()]
    assert plugin.on_search("query", results) == results


def test_plugin_on_config_change_default():
    """on_config_change() has a default no-op implementation."""
    plugin = ConcretePlugin()
    # Should not raise
    plugin.on_config_change(MagicMock())


def test_plugin_get_import_sources_default():
    """get_import_sources() returns empty dict by default."""
    plugin = ConcretePlugin()
    assert plugin.get_import_sources() == {}


def test_plugin_abstract_methods():
    """Plugin cannot be instantiated without implementing abstract methods."""
    with pytest.raises(TypeError):
        Plugin()
