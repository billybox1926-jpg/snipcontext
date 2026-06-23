# Plugin System

Snipcontext's plugin system allows extending core functionality via a unified lifecycle, discovery, and health management framework.

## Architecture

- **Plugin** – abstract base class (ABC) with lifecycle hooks: `on_load`, `on_shutdown`, `on_snippet_saved`.
- **PluginManifest** – dataclass containing plugin metadata (name, version, description, author, dependencies, requires).
- **PluginRegistry** – singleton registry for all plugins; manages discovery, loading, unloading, health checks, and hook runners.
- **Provider factory** – `get_provider(name)` and `list_providers()` use the registry to discover and load providers.
- **Entry points** – plugins are discovered via `snipcontext.plugins` and `snipcontext.providers` groups in `pyproject.toml`.

## Writing Your Own Plugin

1. Pick the right base class:
   - Use `BaseProvider` for new export formats (see [Provider Implementation Guide](providers.md)).
   - Use `Plugin` for lifecycle hooks only (see [Plugin Examples](plugin-examples.md)).
2. Define a `PluginManifest` with `name`, `version`, and `requires`.
3. Implement required methods (`export_single`, `health_check`, ...).
4. Register via entry points in `pyproject.toml`.
5. Test using the patterns in [Plugin Testing Guide](plugin-testing.md).

### Quick example

```python
from snipcontext.plugins.base import Plugin, PluginManifest

class MyPlugin(Plugin):
    manifest = PluginManifest(
        name="my_plugin",
        version="1.0.0",
        description="Example plugin",
        author="You",
        requires=["snipcontext>=0.4.0"],
    )

    def on_load(self) -> None:
        print("Plugin loaded")

    def on_shutdown(self) -> None:
        print("Plugin unloaded")
```

```toml
[project.entry-points."snipcontext.plugins"]
my_plugin = "my_package:MyPlugin"
```

For complete examples, including a Markdown export provider and a JSON audit
logger plugin, see [Plugin Examples](plugin-examples.md).

For testing strategies, mocking patterns, and the compliance test suite, see
[Plugin Testing Guide](plugin-testing.md).

## CLI Commands

- `sc plugins --list` – list all discovered plugins.
- `sc plugins --health` – show health status of loaded plugins.
- `sc plugins --load NAME` – load a plugin by name (calls `on_load`).
- `sc plugins --unload NAME` – unload a plugin by name (calls `on_shutdown`).
- `sc providers --health` – alias that filters to provider-type plugins.

## Version Compatibility

Plugins can specify version constraints in their `requires` field using [PEP 440](https://peps.python.org/pep-0440/) specifiers (e.g., `"snipcontext>=0.3.0,<1.0"`). The registry evaluates these constraints at discovery and skips incompatible plugins.

## Provider-Specific Integration

All built-in providers (`openai`, `claude`, `cursor`, `generic`) are also plugins. They are discovered via the `snipcontext.providers` entry point group and can be loaded/unloaded like any other plugin. The `get_provider(name)` factory function uses the registry to instantiate them.

## Testing

The plugin system is covered by unit tests in `tests/test_plugin_system.py` and `tests/test_registry.py`. When adding a new plugin, please include corresponding tests.
