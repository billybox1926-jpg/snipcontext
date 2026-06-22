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
    """Legacy facade for the plugin registry.

    Delegates all real work to the shared ``PluginRegistry`` singleton
    while keeping the same import surface as before.
    """

    @staticmethod
    def _registry() -> PluginRegistry:
        from snipcontext.plugins.registry import PluginRegistry

        return PluginRegistry()

    @staticmethod
    def discover() -> int:
        return PluginManager._registry().discover()

    @staticmethod
    def load_builtin_providers() -> None:
        return PluginManager._registry().load_builtin_providers()

    @staticmethod
    def get_provider(name: str) -> Any:
        return PluginManager._registry().get_provider(name)

    @staticmethod
    def list_providers() -> dict[str, str]:
        return PluginManager._registry().list_providers()

    @staticmethod
    def list_plugins() -> list[PluginManifest]:
        return PluginManager._registry().list_plugins()

    @staticmethod
    def list_provider_names() -> list[str]:
        return PluginManager._registry().list_provider_names()

    @staticmethod
    def load_plugin(name: str, config: dict[str, Any] | None = None) -> Any:
        return PluginManager._registry().load_plugin(name, config)  # type: ignore[attr-defined]

    @staticmethod
    def unload_plugin(name: str) -> None:
        return PluginManager._registry().unload_plugin(name)  # type: ignore[attr-defined]

    @staticmethod
    def get_plugin(name: str) -> Any:
        return PluginManager._registry().get_plugin(name)

    @staticmethod
    def shutdown() -> None:
        return PluginManager._registry().shutdown()

    @staticmethod
    def run_snippet_saved_hooks(snippet: Any) -> None:
        return PluginManager._registry().run_snippet_saved_hooks(snippet)

    @staticmethod
    def run_search_hooks(query: str, results: Any) -> Any:
        return PluginManager._registry().run_search_hooks(query, results)

    # Backward-compatibility property shims for tests/CLI that inspect internals.
    @property
    def default_provider(self) -> str:
        return PluginManager._registry().default_provider

    @property
    def _providers(self) -> dict[str, Any]:
        registry = PluginManager._registry()
        return {k: v for k, v in registry._plugins.items() if k in registry.list_provider_names()}

    @property
    def _plugins(self) -> dict[str, Any]:
        return PluginManager._registry()._instances

    @property
    def _instances(self) -> dict[str, Any]:
        return PluginManager._registry()._instances

    @property
    def plugins(self) -> dict[str, Any]:
        return self._instances
