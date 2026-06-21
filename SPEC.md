# SnipContext Specification

**Version:** 1.0
**Last updated:** 2026-06-21

This document defines the authoritative contract for SnipContext's behavior.
When in doubt about how something *should* work, check here first.

---

## Core Principles

1. **Local-first** — No network calls. All processing happens on the user's machine.
2. **Git-friendly** — One JSON file per snippet. Human-readable, diffable, mergeable.
3. **Graceful degradation** — If heavy dependencies (sentence-transformers, faiss-cpu) are unavailable, keyword search still works.
4. **Never crash on input** — Malformed files, weird encodings, and edge cases are handled with warnings, not crashes.
5. **Explicit over implicit** — No hidden defaults. If encryption is enabled, the passphrase MUST be set explicitly.

---

## CLI Contract

### Commands

| Command | Input | Output | Side Effects |
|---------|-------|--------|--------------|
| `add` | content (arg/stdin/file), title, tags, language | snippet ID, title, tags | Creates JSON file |
| `get` | snippet ID | snippet content + metadata | None |
| `list` | optional filters (tag, lang) | table of snippets | None |
| `search` | query, optional filters | ranked results with scores | None |
| `delete` | snippet ID, `--force` | confirmation | Removes JSON file |
| `export` | provider, optional query/ids | formatted output (stdout or file) | None |
| `index` | `--force` | progress + count | Rebuilds search index |
| `stats` | None | collection statistics | None |
| `demo` | None | sample snippets | Creates JSON files (only if empty) |
| `watch` | None | None | Starts filesystem watcher |
| `providers` | None | table of providers | None |
| `config path` | None | directory paths | None |
| `encrypt` | snippet ID | confirmation | Re-encrypts content |
| `decrypt` | snippet ID | confirmation | Decrypts content |

### Output Format

- **Table output** (list, search, stats, providers): Rich table with columns
- **Snippet display** (get): Title, language, tags, ID, content
- **Export output** (export): Provider-specific format (XML, Markdown, etc.)
- **Errors**: Red text to stderr, non-zero exit code

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error (not found, validation failure) |
| 2 | Bad parameter / usage error |

---

## Storage Contract

### File Layout

```
~/.local/share/SnipContext/
├── snippets/
│   ├── {uuid}.json
│   └── ...
└── index/
    ├── vector.faiss
    ├── keyword_index.pkl
    └── metadata.json
```

### Snippet JSON Schema

```json
{
  "id": "string (UUID)",
  "content": "string",
  "metadata": {
    "title": "string (required, max 200 chars)",
    "description": "string (default '')",
    "language": "string (enum: python, javascript, ...)",
    "source_url": "string (default '')",
    "author": "string (default '')",
    "confidence": "enum: draft, reviewed, production, reference",
    "llm_optimized": "boolean (default false)"
  },
  "tags": ["string (lowercase, sorted, unique)"],
  "versions": ["array of version objects"],
  "created_at": "ISO 8601 datetime",
  "updated_at": "ISO 8601 datetime",
  "access_count": "integer (default 0)",
  "deleted": "boolean (default false)",
  "encrypted_content": "string (base64, optional)"
}
```

### Rules

- Filenames are `{id}.json`
- Tags are normalized: lowercase, stripped, deduplicated, sorted
- Content hash is computed for integrity verification
- Soft deletion sets `deleted: true` (file is NOT removed)
- Encryption clears plaintext `content` field

---

## Search Contract

### Hybrid Search

```
final_score = semantic_weight * semantic_score + keyword_weight * keyword_score
```

- Default weights: semantic=0.7, keyword=0.3
- Configurable via `SNIPCONTEXT_SEARCH__SEMANTIC_WEIGHT` and `SNIPCONTEXT_SEARCH__KEYWORD_WEIGHT`
- If semantic search unavailable, keyword search runs alone

### Keyword Search

- Uses TF-IDF (sklearn) with unigrams + bigrams
- Stop words removed (english)
- Cosine similarity for ranking

### Semantic Search

- Model: `all-MiniLM-L6-v2` (configurable)
- Index: FAISS (IndexFlatIP for small, IndexIVFFlat for >5000 vectors)
- Embeddings L2-normalized for cosine similarity

---

## Security Contract

### Encryption

- Algorithm: Fernet (AES-128-CBC with HMAC-SHA256)
- Key derivation: PBKDF2-HMAC-SHA256, 100,000 iterations
- Salt: Random 16 bytes, auto-generated on first use, persisted to config
- Passphrase: MUST be set via `SNIPCONTEXT_ENCRYPTION_PASSPHRASE` env var
- **No default passphrase** — tool raises error if not set

### Input Handling

- Snippet content is stored as-is (no sanitization)
- File paths are validated before reading
- Encoding: UTF-8 (fallback to latin-1 with warning)

---

## Error Handling Contract

| Scenario | Behavior |
|----------|----------|
| File not found | Warning message, skip, continue |
| Invalid JSON | Warning message, skip, continue |
| Encoding error | Try latin-1, warn if fails |
| Index corruption | Auto-rebuild index, warn user |
| Missing passphrase (encryption) | Error with instructions |
| Duplicate snippet | Warning, still add (use dedup config) |
| Empty collection | Informative message, no crash |

---

## Configuration Contract

### Precedence (highest to lowest)

1. Environment variables (`SNIPCONTEXT_*`)
2. Config file (`~/.config/SnipContext/snipcontext.yaml`)
3. Defaults (defined in `config/settings.py`)

### Key Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `SNIPCONTEXT_STORAGE__DATA_DIR` | `~/.local/share/SnipContext` | Data directory |
| `SNIPCONTEXT_EMBED_MODEL_NAME` | `all-MiniLM-L6-v2` | Embedding model |
| `SNIPCONTEXT_SEARCH__TOP_K` | `10` | Max search results |
| `SNIPCONTEXT_SEARCH__SEMANTIC_WEIGHT` | `0.7` | Semantic weight in hybrid |
| `SC_AUTO_TAG_ENABLED` | `true` | Enable auto-tag suggestions |
| `SC_AUTO_TAG_AUTO_ACCEPT` | `false` | Auto-accept tag suggestions |
| `SC_DEDUP_ENABLED` | `true` | Enable dedup warnings |
| `SC_DEDUP_THRESHOLD` | `0.95` | Cosine similarity threshold |
| `SNIPCONTEXT_ENCRYPT_ENABLED` | `false` | Enable encryption |
| `SNIPCONTEXT_ENCRYPTION_PASSPHRASE` | (required) | Encryption passphrase |

---

## Versioning

- SPEC version: 1.0
- When behavior changes in a backward-incompatible way, bump SPEC version
- Export output should include version identifier (see #98)
