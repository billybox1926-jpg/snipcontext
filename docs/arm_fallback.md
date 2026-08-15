# ARM/Termux Fallback Behavior

## Overview

SnipContext's semantic search relies on two optional dependencies:

- **sentence-transformers** — provides the embedding model (default: `all-MiniLM-L6-v2`)
- **faiss-cpu** — provides efficient vector similarity search

On **ARM/Linux** (e.g. Raspberry Pi, ARM servers) and **Termux** (Android), these
dependencies may be unavailable, difficult to install, or not performant due to
torch compatibility issues. SnipContext is designed to **gracefully degrade** to
keyword-only search when these deps are missing, without crashing or requiring
user intervention.

## What Triggers the Fallback

The fallback is triggered automatically when either dependency is not importable
at startup. This is detected once at import time in `src/snipcontext/core/embeddings.py`:

```python
try:
    import faiss  # noqa: F401
    _FAISS_AVAILABLE = True
except ImportError:
    _FAISS_AVAILABLE = False

try:
    import sentence_transformers  # noqa: F401
    _SENTENCE_TRANSFORMERS_AVAILABLE = True
except (ImportError, OSError):
    _SENTENCE_TRANSFORMERS_AVAILABLE = False

SEMANTIC_AVAILABLE = _FAISS_AVAILABLE and _SENTANCE_TRANSFORMERS_AVAILABLE
```

When `SEMANTIC_AVAILABLE` is `False`:

1. **HybridSearch** logs a one-time warning at construction (line 117-122 of
   `search_fusion.py`) and continues to operate.
2. **SemanticSearch** and **HybridSearch._semantic_search()** delegate to
   keyword search instead of attempting to use the embedding model.
3. **HybridSearch._hybrid_search()** skips the semantic branch entirely and
   returns keyword-only results.
4. **EmbeddingEngine.model** raises `ImportError` with an actionable message if
   called directly — but this path is only hit by internal auto-tag code, which
   has its own try/except guard.

## How Fallback Affects Search Quality and Performance

| Aspect | With semantic deps | With fallback (keyword-only) |
|--------|--------------------|------------------------------|
| Query understanding | Semantic similarity (e.g. "memory safety" → "Rust ownership") | Exact/stemmed term matching only |
| Ranking | Dense vector similarity + optional keyword fusion | BM25 keyword scores |
| Speed | Embedding encode (first query ~50-200ms, cached after) | Fast (sub-millisecond keyword lookup) |
| Index size | Embedding vectors (~384 dims × snippets) + keyword index | Keyword index only (much smaller) |
| Memory | torch + sentence-transformers model (~90MB RAM) | Minimal (no torch) |
| Storage | `.snipcontext/index.faiss` + keyword index | Keyword index only |

**Practical impact:** On ARM/Termux without semantic deps, searches for exact
terms and code identifiers work just as well as on x86. Searches that rely on
semantic similarity (e.g. finding a snippet by concept rather than by exact
words) will not return results — users should use more specific keywords in that
case.

## Recommendations for Termux Users

1. **Install without semantic extras:**
   ```bash
   pip install snipcontext
   ```
   This skips the heavy torch/sentence-transformers dependency. Keyword search
   works out of the box.

2. **If you have a compatible ARM torch build** (e.g. Termux with pytorch
   installed from the Termux package repository), you can try:
   ```bash
   pip install snipcontext[semantic]
   ```
   This is experimental — torch on Termux may not have GPU support and
   sentence-transformers model download may be slow on mobile networks.

3. **Pre-build the keyword index:** The keyword index is built automatically
   on first search. On slow ARM devices, you can speed up the initial indexing
   by adding snippets gradually rather than in bulk.

4. **Check your fallback status:**
   ```bash
   sc stats
   ```
   The stats output does not currently report semantic availability, but
   checking whether `index.faiss` exists in your `.snipcontext/` directory
   is a proxy: if it's absent and you have snippets, you're in keyword-only
   mode.

5. **Fallback is not a degradation — it's a mode:** SnipContext does not
   distinguish between "degraded" and "normal" operation. Keyword-only mode
   is a fully supported configuration. The CI ARM job runs the full test suite
   in this mode to ensure it remains stable.

## Related

- Issue #171 — Semantic Search Fallback Characterization (ARM/Termux)
- `src/snipcontext/core/embeddings.py` — dependency detection and embedding engine
- `src/snipcontext/core/search_fusion.py` — HybridSearch fallback logic
- `tests/arm/test_fallback.py` — automated fallback characterization tests
