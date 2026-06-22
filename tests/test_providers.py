"""Tests for LLM export providers."""

from __future__ import annotations

import pytest

from snipcontext.core.models import Language, Snippet, SnippetMetadata
from snipcontext.providers.base import ExportFormat
from snipcontext.providers.claude import ClaudeProvider
from snipcontext.providers.cursor import CursorProvider
from snipcontext.providers.generic import GenericProvider
from snipcontext.providers.openai import OpenAIProvider


def create_test_snippets():
    """Create test snippets for export tests."""
    return [
        Snippet(
            content="def hello():\n    print('Hello')",
            metadata=SnippetMetadata(
                title="Hello World",
                description="A greeting function",
                language=Language.PYTHON,
            ),
            tags=["python", "demo"],
        ),
        Snippet(
            content="const add = (a, b) => a + b;",
            metadata=SnippetMetadata(
                title="Add Function",
                description="Simple addition",
                language=Language.JAVASCRIPT,
            ),
            tags=["javascript", "math"],
        ),
    ]


class TestGenericProvider:
    """Tests for the generic Markdown provider."""

    def test_export_single(self):
        provider = GenericProvider()
        snippet = create_test_snippets()[0]
        result = provider.export_single(snippet)

        assert "Hello World" in result
        assert "python" in result
        assert "def hello():" in result
        assert "```python" in result
        # With metadata present, generic should include framework/version/title
        snippet_with_meta = Snippet(
            content="x = 1",
            metadata=SnippetMetadata(
                title="Meta Test",
                description="Test",
                language=Language.PYTHON,
                framework="fastapi",
                version="0.100+",
                author="Dev",
                confidence="production",
                llm_optimized=True,
            ),
            tags=["test"],
        )
        result_with = provider.export_single(snippet_with_meta)
        assert "**Framework:** fastapi" in result_with
        assert "**Version:** 0.100+" in result_with
        assert "**Author:** Dev" in result_with
        assert "**Quality:** production" in result_with
        assert "**LLM-Optimized:** Yes" in result_with

    def test_export_batch(self):
        provider = GenericProvider()
        snippets = create_test_snippets()
        result = provider.export_batch(snippets, title="My Snippets")

        assert "My Snippets" in result
        assert "Hello World" in result
        assert "Add Function" in result

    def test_no_metadata(self):
        provider = GenericProvider(include_metadata=False)
        snippet = create_test_snippets()[0]
        result = provider.export_single(snippet)

        assert "Hello World" in result
        assert "Description:" not in result


class TestClaudeProvider:
    """Tests for the Claude XML provider."""

    def test_export_single(self):
        provider = ClaudeProvider()
        snippet = create_test_snippets()[0]
        result = provider.export_single(snippet)

        assert "<source>" in result
        assert snippet.id in result
        assert "<title>" in result
        assert "Hello World" in result
        assert "<document_content>" in result
        assert "<metadata>" in result

    def test_xml_escaping(self):
        provider = ClaudeProvider()
        snippet = Snippet(
            content="if x < 5 && y > 10: print('hello & world')",
            metadata=SnippetMetadata(
                title="Comparison <operators>",
                description="Test & verify",
            ),
            tags=["test"],
        )
        result = provider.export_single(snippet)
        assert "&lt;" in result or "<operators>" not in result

    def test_metadata_fields(self):
        provider = ClaudeProvider()
        snippet = Snippet(
            content="x = 1",
            metadata=SnippetMetadata(
                title="Meta Test",
                description="Test",
                language=Language.PYTHON,
                framework="fastapi",
                version="0.100+",
                source_url="https://example.com",
                author="Dev",
                confidence="production",
                llm_optimized=True,
            ),
            tags=["test"],
        )
        result = provider.export_single(snippet)
        assert "<framework>fastapi</framework>" in result
        assert "<version>0.100+</version>" in result
        assert "<source_url>https://example.com</source_url>" in result
        assert "<author>Dev</author>" in result
        assert "<confidence>production</confidence>" in result
        assert "<llm_optimized>true</llm_optimized>" in result

    def test_export_batch(self):
        provider = ClaudeProvider()
        snippets = create_test_snippets()
        result = provider.export_batch(snippets)

        assert "<documents>" in result
        assert '<document index="1">' in result
        assert '<document index="2">' in result
        assert "</documents>" in result


class TestCursorProvider:
    """Tests for the Cursor IDE provider."""

    def test_export_single(self):
        provider = CursorProvider()
        snippet = create_test_snippets()[0]
        result = provider.export_single(snippet)

        assert "[source:" in result
        assert "hello_world.py" in result
        assert "```python" in result

    def test_format_type(self):
        assert CursorProvider.format == ExportFormat.MARKDOWN

    def test_metadata_fields(self):
        provider = CursorProvider()
        snippet = Snippet(
            content="x = 1",
            metadata=SnippetMetadata(
                title="Meta Test",
                description="Test",
                language=Language.PYTHON,
                framework="fastapi",
                version="0.100+",
                source_url="https://example.com",
            ),
            tags=["test"],
        )
        result = provider.export_single(snippet)
        assert "// Language: python" in result
        assert "// Framework: fastapi" in result
        assert "// Version: 0.100+" in result
        assert "// Source: https://example.com" in result
        assert "// Tags: test" in result


class TestOpenAIProvider:
    """Tests for the OpenAI provider."""

    def test_export_single(self):
        provider = OpenAIProvider()
        snippet = create_test_snippets()[0]
        result = provider.export_single(snippet)

        assert "SNIPPET:" in result
        assert "Hello World" in result
        assert "═" in result
        assert "```python" in result

    def test_metadata_included(self):
        provider = OpenAIProvider()
        snippet = create_test_snippets()[0]
        result = provider.export_single(snippet)

        assert "Description:" in result
        assert "Language:" in result
        assert "Tags:" in result

    def test_metadata_fields(self):
        provider = OpenAIProvider()
        snippet = Snippet(
            content="x = 1",
            metadata=SnippetMetadata(
                title="Meta Test",
                description="Test",
                language=Language.PYTHON,
                framework="fastapi",
                version="0.100+",
                source_url="https://example.com",
                author="Dev",
                confidence="production",
                llm_optimized=True,
            ),
            tags=["test"],
        )
        result = provider.export_single(snippet)
        assert "Framework: fastapi" in result
        assert "Version: 0.100+" in result
        assert "Source: https://example.com" in result
        assert "Confidence: production" in result
        assert "LLM-Optimized: Yes" in result

    def test_export_batch(self):
        provider = OpenAIProvider()
        snippets = create_test_snippets()
        result = provider.export_batch(snippets, title="Context")

        assert "Context" in result
        assert "SNIPPET:" in result
        assert "Use these as reference" in result


class TestProviderRegistry:
    """Tests for the plugin manager provider registry."""

    def test_load_builtin_providers(self):
        from snipcontext.plugins.base import PluginManager

        pm = PluginManager()
        pm.load_builtin_providers()

        providers = pm.list_providers()
        assert "claude" in providers
        assert "cursor" in providers
        assert "generic" in providers
        assert "openai" in providers

    def test_get_provider(self):
        from snipcontext.plugins.base import PluginManager

        pm = PluginManager()
        pm.load_builtin_providers()

        claude = pm.get_provider("claude")
        assert isinstance(claude, ClaudeProvider)

        generic = pm.get_provider("generic")
        assert isinstance(generic, GenericProvider)

    def test_get_unknown_provider(self):
        from snipcontext.plugins.base import PluginManager

        pm = PluginManager()
        pm.load_builtin_providers()

        with pytest.raises(KeyError):
            pm.get_provider("nonexistent")

    def test_default_provider(self):
        from snipcontext.plugins.base import PluginManager

        pm = PluginManager()
        pm.load_builtin_providers()
        assert pm.default_provider == "generic"
