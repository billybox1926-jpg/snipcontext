"""Tests for the plugin registry and provider factory."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from snipcontext.plugins.base import Plugin, PluginManifest
from snipcontext.plugins.registry import PluginRegistry
from snipcontext.providers import get_provider, list_providers


def test_registry_builtin_providers():
    registry = PluginRegistry()
    registry.load_builtin_providers()
    providers = registry.list_providers()
    assert len(providers) >= 4
    assert "openai" in providers
    assert "claude" in providers


def test_provider_factory_get_provider():
    provider = get_provider("openai")
    assert provider is not None
    assert hasattr(provider.__class__, "manifest")
    assert provider.name == "openai"


def test_provider_factory_list_providers():
    names = list_providers()
    assert "openai" in names
    assert "claude" in names
    assert "cursor" in names
    assert "generic" in names


def _build_test_entry(plugin_name, requires):
    fake_cls = type(
        "TestPlugin",
        (Plugin,),
        {
            "manifest": PluginManifest(
                name=plugin_name,
                version="1.0",
                requires=requires,
            )
        },
    )
    mock_ep = MagicMock()
    mock_ep.name = plugin_name
    mock_ep.load.return_value = fake_cls
    return mock_ep


def test_version_compatibility_compatible():
    PluginRegistry._instance = None
    registry = PluginRegistry()
    mock_ep = _build_test_entry("test_plugin", ["snipcontext>=0.3.0"])

    fake_eps = MagicMock()

    def fake_select(group=None):
        if group == "snipcontext.plugins":
            return []
        return [mock_ep]

    fake_eps.select = MagicMock(side_effect=fake_select)

    with patch(
        "snipcontext.plugins.registry.importlib.metadata.entry_points", return_value=fake_eps
    ):
        registry.discover()
        assert "test_plugin" in registry._plugins


def test_version_compatibility_incompatible():
    PluginRegistry._instance = None
    registry = PluginRegistry()
    mock_ep = _build_test_entry("test_plugin", ["snipcontext>=2.0"])

    fake_eps = MagicMock()

    def fake_select(group=None):
        if group == "snipcontext.plugins":
            return []
        return [mock_ep]

    fake_eps.select = MagicMock(side_effect=fake_select)

    with patch(
        "snipcontext.plugins.registry.importlib.metadata.entry_points", return_value=fake_eps
    ):
        registry.discover()
        assert "test_plugin" not in registry._plugins


def test_version_compatibility_no_constraints():
    PluginRegistry._instance = None
    registry = PluginRegistry()
    mock_ep = _build_test_entry("test_plugin", [])

    fake_eps = MagicMock()

    def fake_select(group=None):
        if group == "snipcontext.plugins":
            return []
        return [mock_ep]

    fake_eps.select = MagicMock(side_effect=fake_select)

    with patch(
        "snipcontext.plugins.registry.importlib.metadata.entry_points", return_value=fake_eps
    ):
        registry.discover()
        assert "test_plugin" in registry._plugins
