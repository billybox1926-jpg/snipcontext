# Search Engine

Semantic and hybrid search guide for SnipContext.

## Index Types

SnipContext uses pluggable vector backends under the hood. The default is
`FlatIP` (exact inner-product search), but you can opt-in to more aggressive
indexes when collections grow large.

| Backend | Memory | Latency (small) | Latency (large) | Accuracy | Notes |
|---------|--------|-----------------|-----------------|----------|-------|
| `flat` | Moderate | Low | High | Exact | Default. No training. |
| `hnsw` | High | Medium | Medium | Approximate | Fast nearby-neighbor graph. No native `remove_ids`. |
| `ivf` | Low | Medium | High | Approximate | Coarse quantizer alone. Best for 10k+ snippets. |
| `ivfpq` | Lowest | Medium | Medium | Approximate | Compressed PQ; best for 50k+ snippets. |

**Recommended settings**

| Collection size | Recommended index type | Notes |
|-----------------|------------------------|-------|
| < 1k snippets | `flat` | Exact search is already fast. |
| 1k – 10k snippets | `hnsw` | Good accuracy/latency tradeoff. |
| 10k – 50k snippets | `ivfpq` | HNSW rebuild threshold hit at ~20% deletions. |
| 50k+ snippets | `ivfpq` with tuned `nlist` / `pq_M` | Train on a representative sample. |

## Auto-switch behavior

By default, SnipContext automatically promotes a `flat` index to `ivfpq`
when the collection size exceeds `auto_index_threshold` (default: 5,000).

You can view or change this with `sc config`:

```bash
sc config get search.auto_index_threshold     # 5000
sc config set search.auto_index_threshold 10000
sc config set search.auto_switch false       # keep flat forever
```

When auto-switch triggers, SnipContext logs:

```
Collection size exceeded threshold (5000). Automatically switching to IVFPQ index.
```

Changing `search.index_type` for a *built* collection requires rebuilding
the vector index:

```bash
sc index rebuild
```

## Keyword fallback

When `faiss-cpu` or `sentence-transformers` are not installed,
SnipContext falls back to keyword-only (BM25) search. All config keys are
still available; the auto-switch will simply return the flat backend.

## Auto-Tagging

The same FAISS index used for semantic search is also used for **auto-tagging**.
When `SC_AUTO_TAG_ENABLED` is true, `sc add` queries the index for the nearest
neighbors, extracts their tags, and surfaces the most frequent ones (above
`SC_AUTO_TAG_MIN_FREQUENCY`).

Auto-tagging and deduplication share the same embedding step, so enabling both
does not incur a second model inference.
