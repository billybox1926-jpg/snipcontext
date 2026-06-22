"""Property-based tests for provider output schema using Hypothesis."""

from __future__ import annotations

from hypothesis import given, settings, strategies as st, HealthCheck
from hypothesis.strategies import sampled_from, builds

import pytest

from snipcontext.core.models import Language, Snippet, SnippetMetadata
from snipcontext.plugins.base import PluginManager


# Strategies for generating snippet data (similar to hybrid test but independent)
snippet_id = st.text(min_size=1, max_size=8, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')))
snippet_content = st.text(min_size=1, max_size=30)
snippet_title = st.text(min_size=1, max_size=20)
snippet_language = sampled_from(list(Language))
snippet_tags = st.lists(st.text(min_size=0, max_size=10), max_size=4, unique=True)

snippet_strategy = builds(
    Snippet,
    id=snippet_id,
    content=snippet_content,
    metadata=builds(
        SnippetMetadata,
        title=snippet_title,
        language=snippet_language,
    ),
    tags=snippet_tags,
)

snippet_lists = st.lists(snippet_strategy, min_size=0, max_size=8)  # allow empty list

provider_name = sampled_from(["openai", "claude", "cursor", "generic"])


@given(provider_name, snippet_lists)
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=50)
def test_provider_export_batch_schema(provider_name: str, snippets: list[Snippet]) -> None:
    """Each built-in provider should return a string and not crash on any snippet list."""
    pm = PluginManager()
    pm.load_builtin_providers()
    provider = pm.get_provider(provider_name)

    # Exercise the provider with include_metadata=True (default) and a title
    output = provider.export_batch(snippets, title="Property Test Schema")
    assert isinstance(output, str), f"{provider_name} did not return a string"

    # Even for empty list, we expect a string (maybe just the title header or empty)
    # We already asserted it's a string; now check it's not None.
    assert output is not None

    # Light format-specific sanity checks (non-exhaustive)
    if provider_name == "claude":
        # Claude XML format: should have <documents> wrapper when there are snippets
        if snippets:
            assert "<documents>" in output
            assert "</documents>" in output
            # Each snippet should be wrapped in <document> tags
            # We'll just check that there is at least one <document> if there are snippets
            assert output.count("<document") >= len(snippets)
    elif provider_name == "cursor":
        # Cursor format: each snippet gets a [source: ...] line
        if snippets:
            # Count of [source: ...] should equal number of snippets
            assert output.count("[source:") == len(snippets)
    elif provider_name == "openai":
        # OpenAI format: each snippet is separated by divider lines
        # The divider is 40 '═' characters repeated twice (i.e., 80?) Actually in code:
        #   _DIVIDER = "═" * 40
        #   lines = [f\"{self._DIVIDER}{self._DIVIDER}\", ...]
        # So we expect to see the divider repeated.
        divider = "═" * 40
        # The output should start and end with divider? Actually:
        #   lines = [
        #           f\"{self._DIVIDER}{self._DIVIDER}\",
        #           f\"  {safe_title}\",
        #           f\"  {len(snippets)} code snippets provided below\",
        #           \"  Use these as reference for your response.\",
        #           f\"{self._DIVIDER}{self._DIVIDER}\",
        #           \"\",
        #       ]
        # Then for each snippet: export_single which adds its own divider block.
        # So we expect at least one occurrence of the double divider.
        assert (divider + divider) in output
    # Generic: just markdown, we can check that if there are snippets, we see at least one header
    elif provider_name == "generic":
        if snippets:
            # Generic output starts with a header for the title, then each snippet as ## Title
            # We'll just check that we see at least one '## ' if there are snippets.
            assert "## " in output or output.strip() == ""  # empty snippets case


@given(st.lists(st.text(min_size=0, max_size=20), min_size=0, max_size=4))
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=25)
def test_plugin_registry_load_plugin_does_not_crash_on_random_names(plugin_names: list[str]) -> None:
    """PluginRegistry.load_plugin should raise ValueError for unknown names, not crash."""
    from snipcontext.plugins.registry import PluginRegistry

    registry = PluginRegistry()
    registry.load_builtin_providers()  # load built-ins so we know what exists

    for name in plugin_names:
        if name in {"claude", "cursor", "openai", "generic"}:
            # These should succeed
            plugin = registry.load_plugin(name)
            assert plugin is not None
        else:
            # Unknown plugin should raise ValueError
            with pytest.raises(ValueError):
                registry.load_plugin(name)