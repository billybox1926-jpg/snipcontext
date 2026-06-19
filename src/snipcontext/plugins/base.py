"""Plugin system for SnipContext.

Plugins can extend SnipContext with new export providers, custom search
strategies, snippet import sources, storage backends, and CLI commands.

Uses Python entry points for discovery, so plugins are automatically
found when installed in the same environment.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from snipcontext.core.models import Snippet
    from snipcontext.providers.base import BaseProvider

logger = logging.getLogger(__name__)

PLUGIN_GROUP = "snipcontext.plugins"
PROVIDER_GROUP = "snipcontext.providers"


class Plugin(ABC):
    """Base class for all SnipContext plugins."""

    name: str = ""
    version: str = "0.1.0"
    description: str = ""

    @abstractmethod
    def activate(self) -> None:
        """Called when the plugin is loaded."""
        ...

    @abstractmethod
    def deactivate(self) -> None:
        """Called when the plugin is unloaded. Override for cleanup."""
        pass

    @abstractmethod
    def on_snippet_saved(self, snippet: Snippet) -> None:
        """Hook called after a snippet is saved."""
        pass

    @abstractmethod
    def on_snippet_loaded(self, snippet: Snippet) -> None:
        """Hook called after a snippet is loaded."""
        pass

    def on_search(self, query: str, results: list) -> list:
        """Hook to modify search results."""
        return results

    def get_import_sources(self) -> dict[str, callable]:
        """Return additional import sources. Map name -> callable."""
        return {}


class PluginManager:
    """Discovers and manages SnipContext plugins."""

    def __init__(self) -> None:
        self._plugins: dict[str, Plugin] = {}
        self._providers: dict[str, type[BaseProvider]] = {}

    def discover(self) -> int:
        """Discover and load all available plugins.

        Returns:
            Number of plugins loaded.
        """
        count = 0

        try:
            from importlib.metadata import entry_points

            eps = entry_points()
            if hasattr(eps, "select"):
                plugin_eps = list(eps.select(group=PLUGIN_GROUP))
                provider_eps = list(eps.select(group=PROVIDER_GROUP))
            else:
                plugin_eps = eps.get(PLUGIN_GROUP, [])
                provider_eps = eps.get(PROVIDER_GROUP, [])

            for ep in plugin_eps:
                try:
                    plugin_class = ep.load()
                    if issubclass(plugin_class, Plugin):
                        plugin = plugin_class()
                        self._plugins[plugin.name] = plugin
                        plugin.activate()
                        count += 1
                        logger.info("Loaded plugin: %s v%s", plugin.name, plugin.version)
                except Exception as exc:
                    logger.error("Failed to load plugin %s: %s", ep.name, exc)

            for ep in provider_eps:
                try:
                    provider_class = ep.load()
                    self._providers[ep.name] = provider_class
                    logger.debug("Registered provider: %s", ep.name)
                except Exception as exc:
                    logger.error("Failed to load provider %s: %s", ep.name, exc)

        except ImportError:
            logger.warning("importlib.metadata not available, plugin discovery disabled")

        return count

    def load_builtin_providers(self) -> None:
        """Register built-in providers without entry points."""
        from snipcontext.providers.claude import ClaudeProvider
        from snipcontext.providers.cursor import CursorProvider
        from snipcontext.providers.generic import GenericProvider
        from snipcontext.providers.openai import OpenAIProvider

        self._providers.update(
            {
                "claude": ClaudeProvider,
                "cursor": CursorProvider,
                "generic": GenericProvider,
                "openai": OpenAIProvider,
            }
        )

    def get_provider(self, name: str) -> BaseProvider:
        """Get a provider instance by name."""
        if name not in self._providers:
            raise KeyError(f"Unknown provider: {name}. Available: {list(self._providers.keys())}")
        return self._providers[name]()

    def list_providers(self) -> dict[str, str]:
        """Return a mapping of provider names to descriptions."""
        result = {}
        for name, cls in self._providers.items():
            try:
                instance = cls()
                result[name] = instance.description or name
            except Exception:
                result[name] = name
        return result

    @property
    def default_provider(self) -> str:
        """Return the default provider name."""
        if "generic" in self._providers:
            return "generic"
        return next(iter(self._providers.keys()), "")

    @property
    def plugins(self) -> dict[str, Plugin]:
        return dict(self._plugins)

    def get_plugin(self, name: str) -> Plugin | None:
        return self._plugins.get(name)

    def shutdown(self) -> None:
        """Deactivate all plugins."""
        for plugin in self._plugins.values():
            try:
                plugin.deactivate()
            except Exception as exc:
                logger.error("Error deactivating plugin %s: %s", plugin.name, exc)
        self._plugins.clear()

    def run_snippet_saved_hooks(self, snippet: Snippet) -> None:
        for plugin in self._plugins.values():
            try:
                plugin.on_snippet_saved(snippet)
            except Exception as exc:
                logger.error("Error in %s on_snippet_saved: %s", plugin.name, exc)

    def run_search_hooks(self, query: str, results: list) -> list:
        for plugin in self._plugins.values():
            try:
                results = plugin.on_search(query, results)
            except Exception as exc:
                logger.error("Error in %s on_search: %s", plugin.name, exc)
        return results
