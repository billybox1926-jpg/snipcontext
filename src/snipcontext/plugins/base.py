"""Plugin system for SnipContext.

Plugins can extend SnipContext with new export providers, custom search
strategies, snippet import sources, storage backends, and CLI commands.

Uses Python entry points for discovery, so plugins are automatically
found when installed in the same environment.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from snipcontext.core.models import Snippet
    from snipcontext.providers.base import BaseProvider

logger = logging.getLogger(__name__)

PLUGIN_GROUP = "snipcontext.plugins"
PROVIDER_GROUP = "snipcontext.providers"
CORE_API_VERSION = "0.3.0"


@dataclass
class PluginManifest:
    """Metadata describing a plugin."""

    name: str
    version: str = "0.1.0"
    api_version: str = CORE_API_VERSION
    dependencies: dict[str, str] = field(default_factory=dict)


class Plugin(ABC):
    """Base class for all SnipContext plugins."""

    manifest: PluginManifest = PluginManifest(name="plugin")

    @abstractmethod
    def on_load(self) -> None:
        """Called when the plugin is loaded."""
        ...

    def on_shutdown(self) -> None:  # noqa: B027
        """Called when the plugin is unloaded. Override for cleanup."""
        ...

    @abstractmethod
    def on_snippet_saved(self, snippet: Snippet) -> None:
        """Hook called after a snippet is saved."""
        ...

    def on_snippet_loaded(self, snippet: Snippet) -> None:  # noqa: B027
        """Hook called after a snippet is loaded."""
        ...

    def on_search(self, query: str, results: list) -> list:
        """Hook to modify search results."""
        return results

    def on_config_change(self, new_config: object) -> None:  # noqa: B027
        """Called when the shared configuration changes."""
        ...

    def get_import_sources(self) -> dict[str, Callable]:
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
                # Legacy interface (Python < 3.10)
                plugin_eps = list(eps.get(PLUGIN_GROUP, ()))
                provider_eps = list(eps.get(PROVIDER_GROUP, ()))

            for ep in plugin_eps:
                try:
                    plugin_class = ep.load()
                    if not issubclass(plugin_class, Plugin):
                        continue
                    manifest = getattr(plugin_class, "manifest", PluginManifest(name=ep.name))
                    if manifest.api_version != CORE_API_VERSION:
                        logger.warning(
                            "Skipping plugin %s: api_version mismatch (plugin=%s, core=%s)",
                            ep.name,
                            manifest.version,
                            CORE_API_VERSION,
                        )
                        continue
                    plugin = plugin_class()
                    self._plugins[manifest.name] = plugin
                    plugin.on_load()
                    count += 1
                    logger.info("Loaded plugin: %s v%s", manifest.name, manifest.version)
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

    def list_plugins(self) -> list[PluginManifest]:
        """Return manifests for loaded plugins."""
        manifests: list[PluginManifest] = []
        for plugin in self._plugins.values():
            manifest = getattr(plugin, "manifest", None)
            if manifest is not None:
                manifests.append(manifest)
        return manifests

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
                plugin.on_shutdown()
            except Exception as exc:
                logger.error("Error deactivating plugin %s: %s", plugin.name, exc)
        self._plugins.clear()
