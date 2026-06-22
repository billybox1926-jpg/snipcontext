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
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from snipcontext.core.models import Snippet
    from snipcontext.plugins.registry import PluginRegistry

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

    def on_search(self, query: str, results: list[Any]) -> list[Any]:
        """Hook to modify search results."""
        return results

    def on_config_change(self, new_config: object) -> None:  # noqa: B027
        """Called when the shared configuration changes."""
        ...

    def get_import_sources(self) -> dict[str, Callable[..., Any]]:
        """Return additional import sources. Map name -> callable."""
        return {}


class PluginManager:
    """Facade for the plugin registry.

    Maintains backward compatibility for existing imports while delegating
    all real work to ``PluginRegistry``.
    """

    def __init__(self) -> None:
        self._registry = _get_registry()

    def discover(self) -> int:
        return self._registry.discover()

    def load_builtin_providers(self) -> None:
        return self._registry.load_builtin_providers()

    def get_provider(self, name: str) -> Any:
        return self._registry.get_provider(name)

    def list_providers(self) -> dict[str, str]:  # type: ignore[name-defined]
        return self._registry.list_providers()

    def list_provider_names(self) -> list[str]:  # type: ignore[name-defined]
        return self._registry.list_provider_names()

    def list_plugins(self) -> list[PluginManifest]:  # type: ignore[name-defined]
        return self._registry.list_plugins()

    @property
    def default_provider(self) -> str:
        return self._registry.default_provider

    @property
    def _providers(self) -> dict[str, Any]:
        return {
            k: v
            for k, v in self._registry._plugins.items()
            if k in self._registry.list_provider_names()
        }

    @property
    def plugins(self) -> dict[str, Plugin]:
        return self._registry._instances

    @property
    def _plugins(self) -> dict[str, Any]:
        return self._registry._instances

    @property
    def _instances(self) -> dict[str, Any]:
        return self._registry._instances

    def get_plugin(self, name: str) -> Plugin | None:
        return self._registry.get_plugin(name)

    def shutdown(self) -> None:
        return self._registry.shutdown()

    def run_snippet_saved_hooks(self, snippet: Any) -> None:
        return self._registry.run_snippet_saved_hooks(snippet)

    def run_search_hooks(self, query: str, results: Any) -> Any:
        return self._registry.run_search_hooks(query, results)


def _get_registry() -> PluginRegistry:
    from snipcontext.plugins.registry import PluginRegistry

    return PluginRegistry()
