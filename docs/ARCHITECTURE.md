# SnipContext Architecture

## Overview

SnipContext is built as a layered architecture with clean separation between data, storage, search, and presentation layers. Every component is designed to be independently testable and replaceable.

```
┌─────────────────────────────────────────────────────────────┐
│                      CLI (Typer + Rich)                      │
├─────────────────────────────────────────────────────────────┤
│  add  │  search  │  get  │  list  │  export  │  delete      │
├─────────────────────────────────────────────────────────────┤
│                  Providers (LLM Exporters)                   │
│   Claude (XML)  │  Cursor  │  OpenAI  │  Generic (MD)        │
├─────────────────────────────────────────────────────────────┤
│                    Search Engine                             │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────┐   │
│  │   Semantic   │  │   Keyword    │  │    Hybrid      │   │
│  │  (FAISS +    │  │  (TF-IDF +   │  │  (weighted     │   │
│  │ embeddings)  │  │  scikit)     │  │  fusion)       │   │
│  └──────────────┘  └──────────────┘  └────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│                   Storage Engine                             │
│     Git-friendly JSON files  +  FAISS vector index          │
├─────────────────────────────────────────────────────────────┤
│                    Data Models (Pydantic)                    │
│         Snippet  │  SnippetMetadata  │  SnippetVersion       │
├─────────────────────────────────────────────────────────────┤
│                  Configuration (Pydantic Settings)           │
│    Env vars  │  YAML file  │  Platform-appropriate dirs       │
├─────────────────────────────────────────────────────────────┤
│                  Plugin System (Entry Points)                │
│    Custom providers  │  Import sources  │  Search hooks       │
└─────────────────────────────────────────────────────────────┘
```

## Core Design Principles

### 1. Local-First
- All data stored on local filesystem
- No network calls required for core functionality
- Embeddings computed locally with sentence-transformers
- FAISS index for fast local similarity search

### 2. Git-Friendly Storage
- Each snippet = one JSON file
- Human-readable, diffable format
- Deterministic serialization (sorted keys, consistent formatting)
- No binary databases or lock files

### 3. Modular Architecture
- Core engine has zero CLI dependencies
- Search engine is pluggable (semantic/keyword/hybrid)
- Providers are independent export formatters
- Plugins use Python entry points for discovery

### 4. Type Safety
- Pydantic v2 models enforce data integrity
- Full type hints throughout
- Runtime validation on all inputs

## Data Flow

### Saving a Snippet
```
User Input → Snippet model (validation) → StorageEngine → JSON file
                                              ↓
                                       VectorIndex (async reindex)
```

### Searching
```
Query → EmbeddingEngine (encode) → FAISS Index (search)
                                          ↓
Query → KeywordIndex (TF-IDF search) → Score Fusion
                                          ↓
                                    StorageEngine (hydrate) → Results
```

### Exporting
```
Snippet IDs / Search Results → Provider (format) → LLM-optimized string
                                                          ↓
                                                   stdout or file
```

## Storage Layout

```
~/.local/share/SnipContext/          # Linux (platformdirs)
~/Library/Application Support/SnipContext/  # macOS
%APPDATA%\\SnipContext\\                   # Windows
├── snippets/
│   ├── abc123def456.json              # Individual snippet files
│   ├── def789ghi012.json
│   └── ...
├── index/
│   ├── vector.faiss                   # FAISS vector index
│   ├── idmap.json                     # FAISS ID → snippet ID mapping
│   └── keyword_index.pkl              # TF-IDF vectorizer + matrix
└── config.yaml                        # User configuration
```

## Search Implementation Details

### Semantic Search
- **Model**: `all-MiniLM-L6-v2` (default) — 384-dim, fast, high quality
- **Index**: FAISS IndexFlatIP (exact inner product = cosine similarity)
- **Scaling**: Automatically switches to IndexIVFFlat for >5000 vectors
- **Normalization**: L2-normalized vectors for cosine similarity

### Keyword Search
- **Method**: TF-IDF with scikit-learn
- **Features**: Unigrams + bigrams, English stop words removed
- **Scoring**: Cosine similarity between query and document vectors

### Hybrid Search
- **Fusion**: `score = w_sem * semantic_score + w_kw * keyword_score`
- **Defaults**: 70% semantic, 30% keyword (configurable)
- **Reciprocal Rank Fusion** also supported for rank-based combination

## Plugin Architecture

Plugins are discovered via Python entry points in the `snipcontext.plugins` group.

```python
# setup.py of a plugin package
entry_points = {
    "snipcontext.plugins": [
        "myplugin = mypackage.plugin:MyPlugin",
    ],
    "snipcontext.providers": [
        "custom = mypackage.provider:CustomProvider",
    ],
}
```

See `plugins/base.py` for the `Plugin` base class with all available hooks.

## Configuration Priority

1. Environment variables (`SNIPCONTEXT_*`)
2. YAML config file (`~/.config/SnipContext/snipcontext.yaml`)
3. Default values in `config/settings.py`

## Performance Characteristics

| Operation | Complexity | Notes |
|-----------|-----------|-------|
| Save snippet | O(1) | Append to filesystem |
| Get snippet | O(1) | Direct file lookup by ID |
| Semantic search | O(n) | FAISS exact search |
| Keyword search | O(n) | Sparse matrix dot product |
| Index build | O(n) | One-time, incremental updates planned |
| Export | O(k) | k = number of snippets exported |
