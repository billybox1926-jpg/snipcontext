# Provider Implementation Guide

This document defines the SnipContext provider contract established in Issue #45.
Every built-in provider (`claude`, `cursor`, `openai`, `generic`) satisfies this
interface, and all third-party providers must do the same.

## Base Class

```python
from snipcontext.providers.base import BaseProvider, ExportFormat, ProviderError
from snipcontext.core.models import Snippet

class MyProvider(BaseProvider):
    name = "myprovider"
    description = "Custom format"
    format = ExportFormat.MARKDOWN

    def export_single(self, snippet: Snippet) -> str:
        raise NotImplementedError

    def export_batch(self, snippets: list[Snippet], title: str = "Code Context") -> str:
        # Optional to override; base provides a generic implementation.
        ...

    def health_check(self) -> str:
        # Return "ok" when the provider is usable without network access.
        raise NotImplementedError
```

## Required Methods

| Method | Signature | Contract |
|--------|-----------|----------|
| `export_single` | `(self, snippet: Snippet) -> str` | Format one snippet for the target LLM/IDE. |
| `export_batch` | `(self, snippets: list[Snippet], title: str = "Code Context") -> str` | Format a multi-snippet context block. |
| `health_check` | `(self) -> str` | Return a status string; prefer `"ok"` for healthy. |

Return annotations must match exactly. Parameter names must match exactly.

## Error Handling

Raise only `ProviderError` (or subclasses) for provider-specific failures.
Do not leak raw provider exceptions through the CLI or plugin loader.

## Metadata

Providers include full `SnippetMetadata` by default (`include_metadata=True`).
Set `include_metadata=False` to export code only.

## Discovery

Providers can be loaded directly or discovered via entry points:

```python
from snipcontext.plugins.base import PluginManager

pm = PluginManager()
pm.load_builtin_providers()
provider = pm.get_provider("generic")
```

Entry-point discovery uses the `snipcontext.providers` group.

## CLI

Base provider interface was previously an experimental internal API; this
version makes it a stable, documented contract. Every provider is expected to
conform so built-in and third-party providers are interchangeable.

## Built-in Providers

| Provider | Format | Best For |
|----------|--------|----------|
| `generic` | Markdown | Universal compatibility |
| `claude` | XML | Anthropic Claude |
| `cursor` | Markdown with file headers | Cursor IDE |
| `openai` | Markdown with dividers | ChatGPT / OpenAI |
