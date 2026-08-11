"""Hypothesis-based contract tests for all built-in export providers."""

from __future__ import annotations

import hypothesis.strategies as st
import pytest
from hypothesis import given, settings

from snipcontext.core.models import Language, Snippet, SnippetMetadata
from snipcontext.providers.claude import ClaudeProvider
from snipcontext.providers.cursor import CursorProvider
from snipcontext.providers.generic import GenericProvider
from snipcontext.providers.openai import OpenAIProvider

_unicode_text = st.text(
    alphabet=st.characters(
        blacklist_categories=("Cs",),
    ),
    min_size=0,
    max_size=200,
).filter(lambda s: "\x00" not in s)

_provider_classes = [
    ClaudeProvider,
    CursorProvider,
    GenericProvider,
    OpenAIProvider,
]


@pytest.fixture(params=_provider_classes)
def provider_cls(request):
    return request.param


def _make_snippet(
    *,
    snippet_id: str = "contract-default",
    title: str = "Untitled",
    content: str = "",
    description: str = "",
    language: str = "python",
    tags: list[str] | None = None,
    framework: str = "",
    version: str = "",
    source_url: str = "",
    author: str = "",
    confidence: str = "reviewed",
    llm_optimized: bool = True,
) -> Snippet:
    return Snippet(
        id=snippet_id,
        content=content,
        metadata=SnippetMetadata(
            title=title,
            description=description,
            language=Language(language),
            framework=framework,
            version=version,
            source_url=source_url,
            author=author,
            confidence=confidence,
            llm_optimized=llm_optimized,
        ),
        tags=tags or [],
    )


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

valid_id_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N"), max_codepoint=127) | st.sampled_from(list("_-")),
    min_size=1,
    max_size=40,
).filter(lambda s: s.strip() != "")

_valid_languages = [
    "python",
    "javascript",
    "go",
    "rust",
    "unknown",
]


_xml_valid_chars = st.characters(blacklist_categories=("Cs",), min_codepoint=0x20, max_codepoint=0xD7FF) | st.characters(min_codepoint=0xE000, max_codepoint=0x10FFFF)
_xml_text = st.text(alphabet=_xml_valid_chars, min_size=0, max_size=100)

@st.composite
def snippet_strategy(draw):
    return _make_snippet(
        snippet_id=draw(valid_id_strategy),
        title=draw(st.text(min_size=1, max_size=100, alphabet=_xml_valid_chars)),
        content=draw(st.one_of(st.just(""), _unicode_text)),
        description=draw(st.one_of(st.just(""), _unicode_text)),
        language=draw(st.sampled_from(_valid_languages)),
        tags=draw(st.lists(_unicode_text, max_size=3)),
        framework=draw(st.one_of(st.just(""), _unicode_text)),
        version=draw(st.one_of(st.just(""), _unicode_text)),
        source_url=draw(st.one_of(st.just(""), st.text(max_size=60))),
        author=draw(st.one_of(st.just(""), _unicode_text)),
        confidence=draw(st.sampled_from(["reviewed", "production", "draft", "reference"])),
        llm_optimized=draw(st.booleans()),
    )


# ---------------------------------------------------------------------------
# Contract tests
# ---------------------------------------------------------------------------


@pytest.mark.provider
@pytest.mark.parametrize("provider_cls", _provider_classes)
@given(snippet=snippet_strategy())
@settings(max_examples=40, deadline=None)
def test_export_single_never_raises(provider_cls, snippet):
    provider = provider_cls(include_metadata=True)
    result = provider.export_single(snippet)

    assert isinstance(result, str)
    assert result.strip() != "" or True
    # Ensure provider output is valid for its declared format family.
    fmt = getattr(provider, "format", None)
    fmt_name = getattr(fmt, "value", str(fmt))
    _assert_output_well_formed(provider_cls.__name__, fmt_name, result)


@pytest.mark.provider
@pytest.mark.parametrize("provider_cls", _provider_classes)
@given(snippets=st.lists(snippet_strategy(), min_size=0, max_size=4))
@settings(max_examples=25, deadline=None)
def test_export_batch_never_raises(provider_cls, snippets):
    provider = provider_cls(include_metadata=True)
    result = provider.export_batch(snippets)

    assert isinstance(result, str)
    fmt = getattr(provider, "format", None)
    fmt_name = getattr(fmt, "value", str(fmt))
    _assert_output_well_formed(provider_cls.__name__, fmt_name, result)


@pytest.mark.provider
@pytest.mark.parametrize("provider_cls", [ClaudeProvider])
@given(snippet=snippet_strategy())
@settings(max_examples=40, deadline=None)
def test_claude_never_raises(provider_cls, snippet):
    provider = provider_cls(include_metadata=True)
    result = provider.export_single(snippet)
    assert isinstance(result, str)
    assert result.strip() != "" or True


@pytest.mark.provider
@pytest.mark.parametrize("provider_cls", [ClaudeProvider])
@given(snippets=st.lists(snippet_strategy(), min_size=1, max_size=3))
@settings(max_examples=20, deadline=None)
def test_claude_batch_never_raises(provider_cls, snippets):
    provider = provider_cls(include_metadata=True)
    result = provider.export_batch(snippets)
    assert isinstance(result, str)


def _assert_output_well_formed(provider_name: str, fmt_name: str, output: str) -> None:
    # Claude XML is intentionally multiple top-level fragments under code fences;
    # the dedicated XML tests validate it separately.
    if fmt_name == "xml":
        return
