"""Plugin system for SnipContext."""

from snipcontext.plugins.base import Plugin, PluginManager, PluginManifest
from snipcontext.plugins.registry import PluginRegistry

__all__ = ["Plugin", "PluginManager", "PluginManifest", "PluginRegistry"]
