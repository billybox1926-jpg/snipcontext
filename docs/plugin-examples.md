# Plugin Examples

This guide provides two complete, runnable examples for extending SnipContext
with custom plugins. Both examples are self-contained and can be tested
independently.

## Example 1: Custom Provider (Markdown Exporter)

This example shows how to create a custom export provider by subclassing
`BaseProvider`. It implements the three required methods and registers via
the `snipcontext.providers` entry point group.

### Step 1: Create the provider class

```python
# my_plugin/provider.py
from __future__ import annotations

from snipcontext.core.models import Snippet
from snipcontext.plugins.base import PluginManifest
from snipcontext.providers.base import BaseProvider, ExportFormat


class MarkdownProvider(BaseProvider):
    """Export snippets as a Markdown document."""

    manifest = PluginManifest(
        name="markdown",
        version="1.0.0",
        description="Export snippets as Markdown",
        author="You",
        requires=["snipcontext>=0.4.0"],
    )

    name = "markdown"
    description = "Markdown export provider"
    format = ExportFormat.MARKDOWN

    def export_single(self, snippet: Snippet) -> str:
        """Format one snippet with optional metadata."""
        lines = []
        meta = snippet.metadata
        if meta.title:
            lines.append(f"## {meta.title}")
        if meta.description:
            lines.append(meta.description)
        if meta.language.value != "unknown":
            lines.append(f"**Language:** {meta.language.value}")
        if snippet.tags:
            lines.append(f"**Tags:** {', '.join(snippet.tags)}")
        lines.append("")
        lines.append(f"```{meta.language.value}")
        lines.append(snippet.content)
        lines.append("```")
        return "\n".join(lines)

    def health_check(self) -> str:
        return "ok"
```

### Step 2: Register in `pyproject.toml`

```toml
[project.entry-points."snipcontext.providers"]
markdown = "my_plugin.provider:MarkdownProvider"
```

### Step 3: Test the provider locally

```python
# tests/test_markdown_provider.py
from __future__ import annotations

import pytest
from snipcontext.core.models import Snippet, SnippetMetadata
from my_plugin.provider import MarkdownProvider


@pytest.fixture()
def provider():
    return MarkdownProvider()


def test_export_single(provider: MarkdownProvider):
    snippet = Snippet(
        content="print('hello')",
        metadata=SnippetMetadata(language="python", title="Hello World"),
    )
    result = provider.export_single(snippet)
    assert "```python" in result
    assert "## Hello World" in result


def test_export_batch(provider: MarkdownProvider):
    snippets = [
        Snippet(
            content="print('a')",
            metadata=SnippetMetadata(language="python"),
        ),
        Snippet(
            content="console.log('b')",
            metadata=SnippetMetadata(language="javascript"),
        ),
    ]
    result = provider.export_batch(snippets, title="My Batch")
    assert "My Batch" in result
    assert "Export schema version:" in result


def test_health_check(provider: MarkdownProvider):
    assert provider.health_check() == "ok"
```

### Step 4: Run the tests

```bash
pytest tests/test_markdown_provider.py -v
```

---

## Example 2: Generic Plugin (JSON Audit Logger)

This example shows how to write a generic plugin (not a provider) that hooks
into snippet lifecycle events. It uses the base `Plugin` class and registers
via the `snipcontext.plugins` entry point group.

### Step 1: Create the plugin class

```python
# my_plugin/audit.py
from __future__ import annotations

import json
import logging
from pathlib import Path

from snipcontext.core.models import Snippet
from snipcontext.plugins.base import Plugin, PluginManifest


class JsonAuditLogger(Plugin):
    """Log every saved snippet to a JSONL audit file."""

    manifest = PluginManifest(
        name="json_audit_logger",
        version="1.0.0",
        description="Append saved snippets to a JSONL audit file",
        author="You",
        requires=["snipcontext>=0.4.0"],
    )

    def on_load(self) -> None:
        self.log_path = Path("snipcontext-audit.jsonl")
        self.logger = logging.getLogger("snipcontext.plugins.json_audit")
        self.logger.info("JSON audit logger loaded: %s", self.log_path)

    def on_shutdown(self) -> None:
        self.logger.info("JSON audit logger unloaded")

    def on_snippet_saved(self, snippet: Snippet) -> None:
        record = {
            "id": snippet.id,
            "content": snippet.content,
            "language": snippet.metadata.language.value,
            "tags": snippet.tags,
            "created_at": snippet.created_at.isoformat(),
        }
        with self.log_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")

    def on_snippet_loaded(self, snippet: Snippet) -> None:
        self.logger.debug("Loaded snippet %s", snippet.id)
```

### Step 2: Register in `pyproject.toml`

```toml
[project.entry-points."snipcontext.plugins"]
json-audit = "my_plugin.audit:JsonAuditLogger"
```

### Step 3: Test the plugin locally

```python
# tests/test_audit_plugin.py
from __future__ import annotations

from pathlib import Path

import pytest

from snipcontext.core.models import Snippet, SnippetMetadata
from snipcontext.plugins.base import PluginManager
from my_plugin.audit import JsonAuditLogger


@pytest.fixture()
def audit_plugin(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Load the audit plugin with an isolated log path."""
    monkeypatch.chdir(tmp_path)
    plugin = JsonAuditLogger()
    plugin.on_load()
    return plugin


def test_on_snippet_saved_creates_jsonl(audit_plugin: JsonAuditLogger, tmp_path: Path):
    snippet = Snippet(
        content="test content",
        metadata=SnippetMetadata(language="python", tags=["test"]),
    )
    audit_plugin.on_snippet_saved(snippet)
    log_path = tmp_path / "snipcontext-audit.jsonl"
    assert log_path.exists()
    import json

    line = json.loads(log_path.read_text(encoding="utf-8"))
    assert line["language"] == "python"
    assert line["tags"] == ["test"]


def test_on_shutdown_completes_cleanly(audit_plugin: JsonAuditLogger):
    audit_plugin.on_shutdown()  # Should not raise
```

### Step 4: Verify entry-point discovery

```python
from snipcontext.plugins.base import PluginManager

pm = PluginManager()
pm.discover()
manifest = next(m for m in pm.list_plugins() if m.name == "json_audit_logger")
assert manifest.version == "1.0.0"
```

---

## Choosing Between Provider and Generic Plugin

| Scenario | Use |
|----------|-----|
| Exporting snippets to a new format | **Provider** (`BaseProvider`) |
| Responding to save/load/search events | **Generic plugin** (`Plugin`) |
| Adding new CLI commands | **Provider** (registry supports `get_provider`) or generic plugin with custom hooks |
| Integrating an external service | **Generic plugin** with `on_load`/`on_shutdown` for connections |

Providers are a specialised subtype of plugins. All providers are plugins,
but not all plugins are providers. If you only need lifecycle hooks
(`on_snippet_saved`, `on_search`, etc.), subclass `Plugin` directly.
