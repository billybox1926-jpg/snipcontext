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
    requires: list[str] = field(default_factory=list)
    description: str = ""
    author: str = ""


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
