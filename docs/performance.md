# Performance Benchmarks

SnipContext is designed to work well for personal and team collections. The table below
gives rough performance expectations on typical development hardware.

| Collection Size | Index Build | Keyword Search | Semantic Search |
|-----------------|-------------|----------------|-----------------|
| 100             | < 1 s       | < 10 ms        | < 100 ms        |
| 1,000           | ~2 s        | < 20 ms        | ~200 ms         |
| 10,000          | ~15 s       | < 50 ms        | ~500 ms         |
| 100,000         | ~2 min      | < 200 ms       | < 2 s           |

**Hardware used:** Intel i7-class CPU, 16 GB RAM.
**Model:** `all-MiniLM-L6-v2` (default semantic model).

Semantic search includes embedding generation and FAISS lookup. Keyword search uses a
sparse TF-IDF-style index (`rank-bm25`) and tends to stay fast even at larger sizes.
The main scaling factor for semantic search is the size of the FAISS index plus the
cost of encoding the query.

If you want realistic numbers for your own collection size and hardware, run the
benchmark script after indexing your snippets:

```bash
python scripts/benchmark.py
```
