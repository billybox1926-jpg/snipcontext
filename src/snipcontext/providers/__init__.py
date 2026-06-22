"""Provider factory and discovery using the plugin registry."""

from __future__ import annotations

from snipcontext.plugins.registry import PluginRegistry


def get_provider(name: str, config: dict | None = None):
    """Load and return a provider instance by name.

    Loads built-in providers if not already loaded.
    """
    registry = PluginRegistry()
    registry.load_builtin_providers()
    return registry.load_plugin(name, config)


def list_providers() -> list[str]:
    """Return names of all available providers."""
    registry = PluginRegistry()
    registry.load_builtin_providers()
    return registry.list_provider_names()


def get_provider_health(name: str) -> dict:
    """Return health status of a provider."""
    registry = PluginRegistry()
    registry.load_builtin_providers()
    return registry.get_health(name)
