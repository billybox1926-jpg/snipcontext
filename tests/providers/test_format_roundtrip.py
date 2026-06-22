"""Formatter roundtrip tests with snapshots (adjusted Phase 3).

Lock in provider output stability by snapshotting ``export_batch`` results
for every built-in provider against canonical inputs.
"""

from __future__ import annotations

from typing import Any

import pytest

from snipcontext.core.models import Language, Snippet, SnippetMetadata
from snipcontext.plugins.base import Plugin
from snipcontext.plugins.registry import PluginRegistry
from snipcontext.providers.base import BaseProvider
from snipcontext.providers.claude import ClaudeProvider
from snipcontext.providers.cursor import CursorProvider
from snipcontext.providers.generic import GenericProvider
from snipcontext.providers.openai import OpenAIProvider


@pytest.fixture(autouse=True)
def _reset_registry():
    PluginRegistry._instance = None
    yield
    PluginRegistry._instance = None


def _build_snippet(
    *,
    snippet_id: str = "snapshot-snippet-default",
    title: str = "Test Snippet",
    description: str = "",
    language: Language = Language.PYTHON,
    content: str = "def hello():\n    print('hello')\n",
    tags: list[str] | None = None,
    framework: str = "fastapi",
    version: str = "0.100+",
    source_url: str = "https://example.com",
    author: str = "Test Author",
    confidence: str = "reviewed",
) -> Snippet:
    return Snippet(
        id=snippet_id,
        content=content,
        metadata=SnippetMetadata(
            title=title,
            description=description,
            language=language,
            framework=framework,
            version=version,
            source_url=source_url,
            author=author,
            confidence=confidence,
            llm_optimized=True,
        ),
        tags=tags or ["python", "demo"],
    )


@pytest.fixture
def canonical_snippets():
    return [
        _build_snippet(
            snippet_id="snapshot-snippet-python-hello",
            title="Hello World",
            content="def hello():\n    print('Hello')\n",
            tags=["python", "demo"],
        ),
        _build_snippet(
            snippet_id="snapshot-snippet-js-add",
            title="Add Function",
            content="const add = (a, b) => a + b;\n",
            language=Language.JAVASCRIPT,
            tags=["javascript", "math"],
            framework="",
        ),
    ]


@pytest.fixture
def empty_snippet_batch():
    return []


@pytest.fixture
def special_chars_snippet_batch():
    return [
        _build_snippet(
            snippet_id="snapshot-snippet-special-chars",
            title="Special <Characters> & Unicode 日本語 🚀",
            content="// special chars\nx = '<>&\"'\nprint('日本語, 🚀')\n",
            description='Tests & <special> "chars" and unicode',
            tags=["test", "edge", "unicode"],
        )
    ]


@pytest.fixture
def minimal_metadata_snippet_batch():
    return [
        _build_snippet(
            snippet_id="snapshot-snippet-minimal-meta",
            title="Minimal Meta",
            content="x = 1\n",
            description="",
            framework="",
            version="",
            source_url="",
            author="",
            tags=[],
        )
    ]


@pytest.fixture(
    params=[
        ClaudeProvider,
        CursorProvider,
        GenericProvider,
        OpenAIProvider,
    ]
)
def provider_cls(request: Any) -> type[BaseProvider]:
    return request.param


def _provider_name(provider: Plugin) -> str:
    return getattr(provider, "name", provider.__class__.__name__)


class TestProviderFormatterOutput:
    def test_batch_snapshot_matches_expected(
        self,
        provider_cls: type[Plugin],
        canonical_snippets: list[Snippet],
        snapshot: Any,
    ) -> None:
        provider = provider_cls(include_metadata=True)
        output = provider.export_batch(canonical_snippets, title="Canonical Context")

        assert isinstance(output, str)
        assert output.strip()

        snapshot.assert_match(output, _provider_name(provider))

    def test_empty_batch_snapshot_is_stable(
        self,
        provider_cls: type[Plugin],
        empty_snippet_batch: list[Snippet],
        snapshot: Any,
    ) -> None:
        provider = provider_cls(include_metadata=True)
        output = provider.export_batch(empty_snippet_batch, title="Empty Context")

        assert isinstance(output, str)

        snapshot.assert_match(output, f"{_provider_name(provider)}-empty")

    def test_special_characters_preserved(
        self,
        provider_cls: type[Plugin],
        special_chars_snippet_batch: list[Snippet],
        snapshot: Any,
    ) -> None:
        provider = provider_cls(include_metadata=True)
        output = provider.export_batch(special_chars_snippet_batch, title="Special Chars")

        assert isinstance(output, str)
        assert output.strip()
        # Snapshot locks exact escaping behavior; test will fire on drift.
        snapshot.assert_match(output, f"{_provider_name(provider)}-special-chars")

    def test_minimal_metadata_snapshot_is_stable(
        self,
        provider_cls: type[Plugin],
        minimal_metadata_snippet_batch: list[Snippet],
        snapshot: Any,
    ) -> None:
        provider = provider_cls(include_metadata=True)
        output = provider.export_batch(minimal_metadata_snippet_batch, title="Minimal Context")

        assert isinstance(output, str)

        snapshot.assert_match(output, f"{_provider_name(provider)}-minimal")
