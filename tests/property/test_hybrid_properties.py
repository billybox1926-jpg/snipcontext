"""Property-based tests for hybrid search invariants using Hypothesis."""

from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import pytest
from hypothesis import given, settings, strategies as st, HealthCheck
from hypothesis.strategies import sampled_from

from snipcontext.core.models import Language, Snippet, SnippetMetadata
from snipcontext.core.search import HybridSearch
from snipcontext.config.settings import Config, EmbeddingConfig, SearchConfig, StorageConfig


# Strategies for generating snippet data
snippet_id = st.text(min_size=1, max_size=8, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')))
snippet_content = st.text(min_size=1, max_size=30)
snippet_title = st.text(min_size=1, max_size=20)
snippet_language = sampled_from(list(Language))
snippet_tags = st.lists(st.text(min_size=0, max_size=10), max_size=4, unique=True)

snippet_strategy = st.builds(
    Snippet,
    id=snippet_id,
    content=snippet_content,
    metadata=st.builds(
        SnippetMetadata,
        title=snippet_title,
        language=snippet_language,
    ),
    tags=snippet_tags,
)

snippet_lists = st.lists(snippet_strategy, min_size=1, max_size=8)
query_str = st.text(min_size=0, max_size=20)


def _make_config(temp_dir: Path) -> Config:
    """Make a config that uses the mock embeddings fixture (zero vectors)."""
    return Config(
        storage=StorageConfig(data_dir=temp_dir, snippets_dir="snippets", index_dir="index"),
        embedding=EmbeddingConfig(model_name="dummy", device="cpu", batch_size=2),
        search=SearchConfig(default_mode="hybrid", semantic_weight=0.5, keyword_weight=0.5, top_k=5, min_score=0.0),
    )


@given(snippet_lists, query_str)
@settings(suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture], max_examples=25)
def test_hybrid_search_idempotency(snippets: list[Snippet], query: str) -> None:
    """Running the same query twice on the same index yields identical results."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        config = _make_config(tmp_path)
        engine = HybridSearch(config)
        engine.index_snippets(snippets)

        results_first = engine.search(query, top_k=5)
        results_second = engine.search(query, top_k=5)

        assert len(results_first) == len(results_second)
        for r1, r2 in zip(results_first, results_second):
            assert r1.snippet.id == r2.snippet.id
            assert r1.score == r2.score
            assert r1.matched_by == r2.matched_by


@given(snippet_lists, query_str)
@settings(suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture], max_examples=25)
def test_hybrid_search_monotonicity_keyword_boost(snippets: list[Snippet], query: str) -> None:
    """Adding a query term to a snippet should not decrease its rank."""
    # We need at least two snippets to test monotonicity.
    if len(snippets) < 2:
        return

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        config = _make_config(tmp_path)
        engine = HybridSearch(config)

        # Pick two distinct snippets
        a, b = snippets[0], snippets[1]

        # Ensure initially that 'a' contains the query term (or a word from it) and 'b' does not.
        # We'll adjust the snippets to make this deterministic for the test.
        # For simplicity, we'll set the content of 'a' to be the query (if not empty) or a fixed term.
        # And set 'b' to have content that does not contain the query term.
        if query:
            a_content = query
            b_content = "unrelated term xyz"
        else:
            a_content = "keyword"
            b_content = "otherword"

        # Update snippets in place (since they are frozen, we need to create new ones)
        a = Snippet(
            id=a.id,
            content=a_content,
            metadata=SnippetMetadata(title=a.metadata.title, language=a.metadata.language),
            tags=a.tags,
        )
        b = Snippet(
            id=b.id,
            content=b_content,
            metadata=SnippetMetadata(title=b.metadata.title, language=b.metadata.language),
            tags=b.tags,
        )

        # Replace the first two snippets in the list with our modified ones
        test_snippets = [a, b] + snippets[2:]

        engine.index_snippets(test_snippets)

        # Get initial ranks (lower rank number = better rank)
        results_initial = engine.search(query, top_k=len(test_snippets))
        id_to_rank_initial = {res.snippet.id: idx for idx, res in enumerate(results_initial)}

        # Now boost snippet b by making its content contain the query term (or a synonym)
        # We'll set b's content to be the query (if not empty) or add the query term.
        if query:
            b_boosted_content = query
        else:
            b_boosted_content = a_content + " " + b_content  # combine to ensure match

        b_boosted = Snippet(
            id=b.id,
            content=b_boosted_content,
            metadata=SnippetMetadata(title=b.metadata.title, language=b.metadata.language),
            tags=b.tags,
        )

        # Replace b with the boosted version
        test_snippets_boosted = [a, b_boosted] + snippets[2:]

        # Rebuild index with the boosted snippet
        engine.index_snippets(test_snippets_boosted)

        results_boosted = engine.search(query, top_k=len(test_snippets_boosted))
        id_to_rank_boosted = {res.snippet.id: idx for idx, res in enumerate(results_boosted)}

        # The rank of b should be <= (i.e., not worse than) its initial rank.
        initial_rank_b = id_to_rank_initial.get(b.id, len(test_snippets))
        boosted_rank_b = id_to_rank_boosted.get(b.id, len(test_snippets_boosted))

        assert boosted_rank_b <= initial_rank_b, (
            f"Boosted snippet b rank worsened: initial {initial_rank_b}, boosted {boosted_rank_b}"
        )


@given(snippet_lists, query_str)
@settings(suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture], max_examples=25)
def test_hybrid_search_consistency_adding_irrelevant(snippets: list[Snippet], query: str) -> None:
    """Adding an irrelevant snippet (no semantic or keyword overlap) should not change ranking of originals."""
    if len(snippets) < 1:
        return

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        config = _make_config(tmp_path)
        engine = HybridSearch(config)

        # Build index with original snippets
        engine.index_snippets(snippets)
        results_original = engine.search(query, top_k=len(snippets))
        original_ids_in_order = [res.snippet.id for res in results_original]

        # Create an irrelevant snippet: content that shares no words with query and a random ID
        # We'll make its content a string of 'z's to avoid matching any typical query.
        irrelevant_content = "zzzzzzzz"
        irrelevant_snippet = Snippet(
            id="irrelevant-" + np.random.default_rng().bytes(4).hex(),
            content=irrelevant_content,
            metadata=SnippetMetadata(title="Irrelevant", language=Language.UNKNOWN),
            tags=[],
        )

        # Add the irrelevant snippet and rebuild
        snippets_with_irrelevant = snippets + [irrelevant_snippet]
        engine.index_snippets(snippets_with_irrelevant)
        results_with_irrelevant = engine.search(query, top_k=len(snippets))

        # The ordering of the original snippet IDs should be preserved.
        ids_with_irrelevant = [res.snippet.id for res in results_with_irrelevant if res.snippet.id in original_ids_in_order]
        assert ids_with_irrelevant == original_ids_in_order, (
            f"Original snippet order changed after adding irrelevant snippet.\n"
            f"Original: {original_ids_in_order}\n"
            f"With irrelevant: {ids_with_irrelevant}"
        )


# Strategy for generating a provider name from the built-in set
provider_name = sampled_from(["openai", "claude", "cursor", "generic"])


@given(provider_name, snippet_lists)
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=50)
def test_provider_export_batch_returns_string(provider_name: str, snippets: list[Snippet]) -> None:
    """Each built-in provider should return a non-empty string for any snippet list."""
    from snipcontext.plugins.base import PluginManager

    pm = PluginManager()
    pm.load_builtin_providers()
    provider = pm.get_provider(provider_name)

    # Include metadata to exercise more code paths
    output = provider.export_batch(snippets, title="Property Test")
    assert isinstance(output, str)
    assert len(output) > 0

    # For structured formats, we can do a very light sanity check.
    if provider_name == "claude":
        # Claude XML should contain <documents> and </documents>
        assert "<documents>" in output
        assert "</documents>" in output
    elif provider_name == "cursor":
        # Cursor format should have at least one [source: ...] line if there are snippets
        if snippets:
            assert "[source:" in output
    elif provider_name == "openai":
        # OpenAI format should have the divider lines
        assert "═" * 40 in output  # the divider is 40 '═' chars
    # Generic is just markdown, no strict structure to check