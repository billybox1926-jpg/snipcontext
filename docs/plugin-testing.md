# Plugin Testing Guide

This guide covers testing strategies for SnipContext plugins:
unit tests, integration tests, mocking patterns, and the compliance test suite.

## Unit Testing a Plugin

Use `pytest` with isolated fixtures. Because plugins are discovered via entry
points, you can instantiate them directly in tests without touching the global
`PluginRegistry`.

### Minimal provider test

```python
from __future__ import annotations

import pytest
from snipcontext.core.models import Snippet, SnippetMetadata
from my_plugin.provider import MarkdownProvider


@pytest.fixture()
def provider():
    return MarkdownProvider()


def test_health_check(provider: MarkdownProvider):
    assert provider.health_check() == "ok"


def test_export_single(provider: MarkdownProvider):
    snippet = Snippet(
        content="x = 1",
        metadata=SnippetMetadata(language="python"),
    )
    result = provider.export_single(snippet)
    assert "```python" in result
    assert "x = 1" in result
```

### Minimal generic plugin test

```python
from __future__ import annotations

from pathlib import Path
import pytest
from snipcontext.core.models import Snippet, SnippetMetadata
from my_plugin.audit import JsonAuditLogger


@pytest.fixture()
def audit_plugin(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    plugin = JsonAuditLogger()
    plugin.on_load()
    return plugin


def test_on_snippet_saved_creates_jsonl(audit_plugin: JsonAuditLogger, tmp_path: Path):
    snippet = Snippet(
        content="test content",
        metadata=SnippetMetadata(language="python"),
    )
    audit_plugin.on_snippet_saved(snippet)
    log_path = tmp_path / "snipcontext-audit.jsonl"
    assert log_path.exists()
```

## Integration Testing with the PluginRegistry

To verify that your plugin is discoverable via entry points, use
`PluginRegistry` directly.

```python
from __future__ import annotations

import pytest
from snipcontext.plugins.base import PluginManager, PluginRegistry


def test_plugin_discovery():
    pm = PluginManager()
    count = pm.discover()
    manifests = pm.list_plugins()
    names = [m.name for m in manifests]
    assert "json_audit_logger" in names
    assert manifests[names.index("json_audit_logger")].version == "1.0.0"


def test_plugin_load_and_unload():
    pm = PluginManager()
    pm.discover()
    plugin = pm.load_plugin("json_audit_logger")
    assert plugin is not None
    health = pm.get_health("json_audit_logger")
    assert health["status"] == "ok"
    pm.unload_plugin("json_audit_logger")
```

### Resetting registry state between tests

```python
@pytest.fixture(autouse=True)
def _reset_registry():
    """Force a fresh registry per test to avoid cross-test pollution."""
    PluginRegistry._instance = None
    yield
    PluginRegistry._instance = None
```

## Mocking External Dependencies

If your plugin calls external services (HTTP APIs, databases), mock those
calls so tests remain fast and deterministic.

```python
from unittest.mock import patch, MagicMock
import pytest


def test_remote_provider_with_mock(provider):
    with patch("my_plugin.provider.httpx.post") as mock_post:
        mock_post.return_value.json.return_value = {"result": "ok"}
        snippet = Snippet(content="test")
        result = provider.export_single(snippet)
        mock_post.assert_called_once()
        assert "ok" in result
```

## Using `CliRunner` for Plugin CLI Integration

If your plugin registers CLI commands, test them with Typer's `CliRunner`.

```python
from typer.testing import CliRunner
from my_plugin.cli import app as plugin_app

runner = CliRunner()


def test_plugin_cli_command():
    result = runner.invoke(plugin_app, ["status"])
    assert result.exit_code == 0
    assert "ok" in result.output
```

## Compliance Test Suite

SnipContext ships with an interface compliance suite. Run it against your
provider to catch signature mismatches and missing methods.

```bash
pytest tests/test_registry.py -k "provider"
```

If the suite includes a generic `test_provider_interface` test, it will
exercise `export_single`, `export_batch`, and `health_check` against a
minimal `Snippet` fixture.

## Coverage Checklist for New Plugins

| Test | Covers |
|------|--------|
| `test_health_check` | Provider returns `"ok"` without side effects |
| `test_export_single` | Single-snippet formatting |
| `test_export_batch` | Multi-snippet formatting + schema version header |
| `test_on_snippet_saved` | Plugin hook writes expected side effect |
| `test_discovery` | Entry point is discoverable via `importlib.metadata` |
| `test_load_unload` | Registry can load and unload the plugin cleanly |
| `test_error_paths` | Provider raises `ProviderError` on invalid input |
