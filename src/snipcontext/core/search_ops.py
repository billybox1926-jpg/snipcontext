"""Search and export domain business logic.

Pure functions for search and export operations.
No I/O, no CLI dependencies.
"""

from __future__ import annotations

from snipcontext.core.models import Snippet
from snipcontext.core.search import HybridSearch
from snipcontext.core.storage import StorageEngine
from snipcontext.plugins.base import PluginManager


def ensure_index(
    storage: StorageEngine,
    search: HybridSearch,
    force: bool = False,
) -> list[Snippet]:
    """Ensure the search index is built.

    Args:
        storage: Storage engine instance.
        search: Hybrid search instance.
        force: Force rebuild even if index exists.

    Returns:
        List of active (non-deleted) snippets.
    """
    snippets = storage.list_all()
    active = [s for s in snippets if not s.deleted]

    if force or not search.indices_ready:
        if active:
            search.index_snippets(active)

    return active


def search_snippets(
    storage: StorageEngine,
    search: HybridSearch,
    query: str,
    mode: str = "hybrid",
    top_k: int = 10,
    threshold: float | None = None,
    fuzzy: bool = False,
) -> list:
    """Search snippets using the hybrid search engine.

    Args:
        storage: Storage engine instance.
        search: Hybrid search instance.
        query: Search query string.
        mode: Search mode — 'semantic', 'keyword', 'hybrid', 'tag'.
        top_k: Maximum number of results.
        threshold: Minimum relevance score (optional).
        fuzzy: Enable fuzzy matching for keyword search.

    Returns:
        List of SearchResult instances.
    """
    active = ensure_index(storage, search)
    if not active:
        return []

    results = search.search(
        query,
        top_k=top_k,
        mode=mode,
        min_score=threshold,
        fuzzy=fuzzy,
    )
    return results


def export_snippets(
    storage: StorageEngine,
    search: HybridSearch,
    provider_name: str,
    query: str | None = None,
    ids: list[str] | None = None,
    top_k: int = 10,
) -> tuple[list[Snippet], str]:
    """Collect and format snippets for export.

    Args:
        storage: Storage engine instance.
        search: Hybrid search instance.
        provider_name: Export provider name (e.g., 'generic', 'claude').
        query: Search query to filter snippets (optional).
        ids: Specific snippet IDs to export (optional).
        top_k: Max results when using query.

    Returns:
        Tuple of (snippets_list, formatted_output_string).

    Raises:
        KeyError: If provider_name is not found.
    """
    pm = PluginManager()
    pm.load_builtin_providers()
    prov = pm.get_provider(provider_name)

    snippets: list[Snippet] = []

    if ids:
        for sid in ids:
            try:
                snippets.append(storage.get(sid))
            except Exception:
                pass  # Skip not-found IDs
    elif query:
        results = search_snippets(storage, search, query, top_k=top_k)
        snippets = [r.snippet for r in results]
    else:
        snippets = storage.list_all()

    formatted = prov.export_batch(snippets)
    return snippets, formatted
