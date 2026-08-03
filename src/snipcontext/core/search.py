"""Backward-compatible re-exports for ``snipcontext.core.search``.

This module used to contain the full search implementation (~1230 lines):
EmbeddingEngine, VectorIndex, KeywordIndex, SemanticSearch, and HybridSearch.
It has been split into focused modules:

- ``snipcontext.core.embeddings``            — EmbeddingEngine, SEMANTIC_AVAILABLE
- ``snipcontext.core.indexes.vector_index``  — VectorIndex
- ``snipcontext.core.indexes.keyword_index`` — KeywordIndex
- ``snipcontext.core.search_fusion``         — SemanticSearch, HybridSearch

This module re-exports the same public names from their new locations so
existing imports of ``snipcontext.core.search.X`` (and
``from snipcontext.core.search import X``) continue to work unchanged.

New code should import directly from the modules above; this shim may be
removed in a future release once call sites have migrated.
"""

from __future__ import annotations

from snipcontext.core.embeddings import SEMANTIC_AVAILABLE, EmbeddingEngine
from snipcontext.core.indexes.keyword_index import KeywordIndex
from snipcontext.core.indexes.vector_index import VectorIndex
from snipcontext.core.search_fusion import HybridSearch, SemanticSearch

__all__ = [
    "SEMANTIC_AVAILABLE",
    "EmbeddingEngine",
    "VectorIndex",
    "KeywordIndex",
    "SemanticSearch",
    "HybridSearch",
]
