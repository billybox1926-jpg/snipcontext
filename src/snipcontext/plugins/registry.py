"""Plugin registry – central discovery, lifecycle, and health management."""

from __future__ import annotations

import importlib.metadata
import logging
import re
from typing import TYPE_CHECKING, Any

from packaging import specifiers
from packaging.version import Version

import snipcontext

from .base import CORE_API_VERSION, Plugin, PluginManifest

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

PLUGIN_GROUP = "snipcontext.plugins"
PROVIDER_GROUP = "snipcontext.providers"


class PluginRegistry:
    """Singleton registry for all SnipContext plugins."""

    _instance: PluginRegistry | None = None

    def __new__(cls) -> PluginRegistry:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return
        self._plugins: dict[str, type[Any]] = {}
        self._instances: dict[str, Any] = {}
        self._manifests: dict[str, PluginManifest] = {}
        self._loaded: dict[str, bool] = {}
        self._discovered = False
        self._initialized = True

    def _is_compatible(self, manifest: PluginManifest) -> bool:
        current = Version(snipcontext.__version__)
        if manifest.requires:
            for raw_req in manifest.requires:
                req = re.sub(r"^[a-zA-Z0-9_.-]+\s*", "", raw_req.strip())
                spec = specifiers.SpecifierSet(req)
                if not spec.contains(current):
                    return False
            return True
        return manifest.api_version == CORE_API_VERSION

    def discover(self) -> int:
        """Discover and load all available plugins via entry points."""
        if self._discovered:
            return sum(self._loaded.values())
        count = 0
        try:
            eps = importlib.metadata.entry_points()
            try:
                plugin_eps = list(eps.select(group=PLUGIN_GROUP))
            except AttributeError:
                plugin_eps = list(eps.get(PLUGIN_GROUP, ()))
            try:
                provider_eps = list(eps.select(group=PROVIDER_GROUP))
            except AttributeError:
                provider_eps = list(eps.get(PROVIDER_GROUP, ()))

            for ep in plugin_eps:
                try:
                    plugin_cls = ep.load()
                    if not issubclass(plugin_cls, Plugin):
                        continue
                    manifest = getattr(plugin_cls, "manifest", None)
                    if not isinstance(manifest, PluginManifest):
                        logger.warning("Plugin %s missing manifest, skipping", ep.name)
                        continue
                    if not self._is_compatible(manifest):
                        logger.info(
                            "Skipping plugin %s: version incompatible (requires=%s)",
                            ep.name,
                            manifest.requires or manifest.api_version,
                        )
                        continue
                    plugin = plugin_cls()
                    self._plugins[manifest.name] = plugin_cls
                    self._manifests[manifest.name] = manifest
                    self._loaded[manifest.name] = False
                    plugin.on_load()
                    self._loaded[manifest.name] = True
                    count += 1
                    logger.info("Loaded plugin: %s v%s", manifest.name, manifest.version)
                except Exception as exc:
                    logger.error("Failed to load plugin %s: %s", ep.name, exc)

            for ep in provider_eps:
                try:
                    provider_cls = ep.load()
                    if not issubclass(provider_cls, Plugin):
                        continue
                    manifest = getattr(provider_cls, "manifest", None)
                    if not isinstance(manifest, PluginManifest):
                        logger.warning("Provider %s missing manifest, skipping", ep.name)
                        continue
                    if not self._is_compatible(manifest):
                        logger.info(
                            "Skipping provider %s: version incompatible (requires=%s)",
                            ep.name,
                            manifest.requires or manifest.api_version,
                        )
                        continue
                    self._plugins[ep.name] = provider_cls
                    self._loaded[ep.name] = False
                except Exception as exc:
                    logger.error("Failed to load provider %s: %s", ep.name, exc)

        except ImportError:
            logger.warning("importlib.metadata not available, plugin discovery disabled")
        self._discovered = True
        return count

    def load_builtin_providers(self) -> None:
        """Register built-in providers without entry points."""
        from snipcontext.providers.claude import ClaudeProvider
        from snipcontext.providers.cursor import CursorProvider
        from snipcontext.providers.generic import GenericProvider
        from snipcontext.providers.openai import OpenAIProvider

        self._plugins.update(
            {
                "claude": ClaudeProvider,
                "cursor": CursorProvider,
                "generic": GenericProvider,
                "openai": OpenAIProvider,
            }
        )
        for name, cls in list(self._plugins.items()):
            if name not in self._instances:
                try:
                    instance = cls()
                    self._instances[name] = instance
                    self._loaded[name] = True
                    if hasattr(instance, "on_load"):
                        instance.on_load()
                except Exception as exc:
                    logger.error("Failed to instantiate builtin provider %s: %s", name, exc)

    def load_plugin(self, name: str, config: dict[str, Any] | None = None) -> Any:
        """Instantiate and initialise a plugin by name."""
        self.discover()
        if name not in self._plugins:
            raise ValueError(f"Plugin '{name}' not found")
        if self._loaded.get(name, False):
            return self._instances[name]
        plugin_cls = self._plugins[name]
        plugin = plugin_cls()
        if hasattr(plugin, "on_load"):
            plugin.on_load()
        self._instances[name] = plugin
        self._loaded[name] = True
        return plugin

    def unload_plugin(self, name: str) -> None:
        """Call on_shutdown and discard the plugin instance."""
        self.discover()
        if not self._loaded.get(name, False):
            raise ValueError(f"Plugin '{name}' is not loaded")
        plugin = self._instances[name]
        if hasattr(plugin, "on_shutdown"):
            plugin.on_shutdown()
        del self._instances[name]
        self._loaded[name] = False

    def get_health(self, name: str) -> dict[str, Any]:
        """Return health status from a loaded plugin."""
        if not self._loaded.get(name, False):
            raise ValueError(f"Plugin '{name}' is not loaded")
        plugin = self._instances[name]
        if hasattr(plugin, "health_check"):
            return {"status": plugin.health_check()}
        return {"status": "ok"}

    def get_provider(self, name: str) -> Any:
        """Get a provider instance by name."""
        if name not in self._plugins:
            raise KeyError(f"Unknown provider: {name}. Available: {list(self._plugins.keys())}")
        if name in self._instances:
            return self._instances[name]
        provider_cls = self._plugins[name]
        provider = provider_cls()
        self._instances[name] = provider
        self._loaded[name] = True
        return provider

    def list_providers(self) -> dict[str, str]:
        """Return a mapping of provider names to descriptions."""
        result: dict[str, str] = {}
        for name in self.list_provider_names():
            try:
                provider = self.get_provider(name)
                result[name] = getattr(provider, "description", "") or name
            except Exception:
                result[name] = name
        return result

    def list_provider_names(self) -> list[str]:
        if not self._discovered:
            self.discover()
        names = []
        from snipcontext.providers.base import BaseProvider

        for name, plugin_cls in self._plugins.items():
            if isinstance(plugin_cls, type) and issubclass(plugin_cls, BaseProvider):
                names.append(name)
        return names

    def list_plugins(self) -> list[PluginManifest]:
        """Return manifests for loaded plugins."""
        manifests: list[PluginManifest] = []
        seen = set()
        for plugin in self._instances.values():
            manifest = getattr(plugin, "manifest", None)
            if isinstance(manifest, PluginManifest) and manifest.name not in seen:
                manifests.append(manifest)
                seen.add(manifest.name)
        for manifest in self._manifests.values():
            if manifest.name not in seen:
                manifests.append(manifest)
                seen.add(manifest.name)
        return manifests

    @property
    def default_provider(self) -> str:
        if "generic" in self._plugins:
            return "generic"
        return next(iter(self._plugins.keys()), "")

    def get_plugin(self, name: str) -> Plugin | None:
        return self._instances.get(name)

    def shutdown(self) -> None:
        """Deactivate all plugins."""
        for plugin in self._instances.values():
            try:
                plugin.on_shutdown()
            except Exception as exc:
                logger.error(
                    "Error deactivating plugin %s: %s", getattr(plugin, "manifest", None), exc
                )
        self._instances.clear()
        self._loaded = {k: False for k in self._loaded}

    def run_snippet_saved_hooks(self, snippet: Any) -> None:
        for plugin in self._instances.values():
            try:
                plugin.on_snippet_saved(snippet)
            except Exception as exc:
                logger.error(
                    "Error in %s on_snippet_saved: %s", getattr(plugin, "manifest", None), exc
                )

    def run_search_hooks(self, query: str, results: Any) -> Any:
        for plugin in self._instances.values():
            try:
                results = plugin.on_search(query, results)
            except Exception as exc:
                logger.error("Error in %s on_search: %s", getattr(plugin, "manifest", None), exc)
        return results
