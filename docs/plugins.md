# Plugin System

SnipContext plugins let you extend the application with custom providers,
hooks, and lifecycle logic without modifying core code.

## Architecture

- `PluginBase` — abstract base for all plugins.
- `PluginManifest` — metadata describing the plugin.
- `PluginManager` — discovers, loads, and manages plugins.

## Manifest

```python
from dataclasses import dataclass, field
from snipcontext.plugins.base import PluginManifest

manifest = PluginManifest(
    name="my-plugin",
    version="0.1.0",
    api_version="0.3.0",
    dependencies={"snipcontext": ">=0.3.0"},
)
```

## Lifecycle Hooks

| Hook | When Called |
|------|-------------|
| `on_load()` | Immediately after plugin import and instantiation. |
| `on_config_change(new_config)` | When shared configuration is updated. |
| `on_shutdown()` | During application shutdown. |
| `on_snippet_saved(snippet)` | After a snippet is persisted. |
| `on_snippet_loaded(snippet)` | After a snippet is loaded. |
| `on_search(query, results)` | After search completes; can reorder results. |

## Discovery

Plugins are discovered via Python entry points:

- Group `snipcontext.plugins` — general plugins.
- Group `snipcontext.providers` — provider plugins.

```python
pm = PluginManager()
pm.discover()  # loads entry points
pm.load_builtin_providers()  # registers built-in providers
```

Version mismatches (`api_version`) are logged and skipped.

## CLI Commands

```bash
sc plugins --list
sc plugins --health
sc providers --health
```
