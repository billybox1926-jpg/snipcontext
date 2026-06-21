# SnipContext

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Ruff](https://img.shields.io/badge/lint-ruff-261230?logo=ruff&logoColor=white)](https://github.com/astral-sh/ruff)
[![Mypy](https://img.shields.io/badge/types-mypy-2C3E50?logo=python&logoColor=white)](https://mypy-lang.org/)
[![CI](https://github.com/billybox1926-jpg/snipcontext/actions/workflows/ci.yml/badge.svg)](../../actions/workflows/ci.yml)
[![Contributors](https://img.shields.io/github/contributors/billybox1926-jpg/snipcontext)](../../graphs/contributors)
[![Last Commit](https://img.shields.io/github/last-commit/billybox1926-jpg/snipcontext)](../../commits/master)
[![Issues](https://img.shields.io/github/issues/billybox1926-jpg/snipcontext)](../../issues)

![SnipContext Infographic](docs/snipcontext-infographic.png)

**AI-powered code snippet & context manager.**

Save, search, tag, and instantly inject your best boilerplate, patterns, and context into any LLM (Claude, Cursor, Grok, Windsurf, etc.).

> **Local-first** — Open source — Built for humans + AI agents

---

## Why SnipContext?

- **Stop rewriting** the same auth flows, component patterns, or utility functions
- **Stop feeding LLMs** messy or outdated code from your clipboard history
- **Build your personal/team "second brain"** of high-quality, reusable code
- **Semantic search** finds code by meaning, not just keywords
- **LLM-optimized exports** format your snippets for maximum comprehension

---

## Key Features

| Feature | Status | Description |
|---------|--------|-------------|
| Rich snippet saving with tags, metadata, and versioning | ✅ | Full CRUD with soft-delete and encryption |
| **Semantic search** with local embeddings | ✅ | sentence-transformers + FAISS, runs offline |
| **Hybrid search** — semantic + keyword fusion | ✅ | Configurable weights, TF-IDF + embeddings |
| LLM-optimized export providers | ✅ | Claude XML, Cursor, OpenAI, Generic Markdown |
| Auto-tagging via embeddings | ✅ | Suggests tags based on similar snippets |
| Similarity-based deduplication | ✅ | Warns when adding near-duplicate snippets |
| Encryption at rest | ✅ | Fernet (AES-128) with PBKDF2 key derivation |
| File watchdog / real-time indexing | ✅ | Auto-reindex on file changes |
| Plugin system | ✅ | Entry points for providers and exporters |
| CLI + Python library | ✅ | Use from terminal or import as a module |
| Git-friendly local-first storage | ✅ | One JSON file per snippet, easy to version |

### Supported LLM Providers

| Provider | Format | Best For |
|----------|--------|----------|
| **Generic** | Markdown | Universal compatibility |
| **Claude** | XML documents | Anthropic Claude |
| **Cursor** | File-style headers | Cursor IDE |
| **OpenAI** | Delineated sections | ChatGPT / GPT-4 |

---

## Quick Start

### Installation

```bash
# From PyPI with uv (recommended — faster installs, better dependency resolution)
uv tool install snipcontext

# From PyPI with pip
pip install snipcontext

# From source (after cloning)
cd snipcontext
uv sync                    # install all deps (including dev)
uv run sc --help           # run without activating venv

# Or with pip (traditional)
pip install -e ".[dev]"
```

> **💡 Why uv?** This project uses \`uv\` for dependency management (\`uv.lock\` pinned). \`uv sync\` guarantees reproducible installs. \`pip install\` works but may resolve dependencies differently.
# Or install directly from GitHub
pip install git+https://github.com/billybox1926-jpg/snipcontext.git
```

> **📦 Dependency Footprint:** SnipContext installs `sentence-transformers` and `faiss-cpu` for local semantic search. These are substantial dependencies (~500MB download). If you only need keyword search, the tool still works — semantic features gracefully degrade when these packages are unavailable.

> **⚠️ Windows Users:** Windows has a built-in `sc.exe` (Service Control) that shadows the `sc` CLI entry point. Use the full command name `snipcontext` instead, or run via `python -m snipcontext`.

### Security Considerations

- **Encryption at rest:** Uses Fernet (AES-128-CBC with HMAC) with PBKDF2 key derivation (100k iterations). Passphrase is read from `SNIPCONTEXT_ENCRYPTION_PASSPHRASE` env var — **never pass it on the command line** (shell history leak).
- **No default passphrase:** If encryption is enabled but `SNIPCONTEXT_ENCRYPTION_PASSPHRASE` is not set, the tool raises an error rather than falling back to a known default. This prevents a false sense of security.
- **stdin for sensitive content:** Use `sc add --file secret.py` or pipe via stdin (`cat secret.py | sc add --file`) to avoid shell history leaks with `--encrypt`.
- **Salt:** Auto-generated on first use and persisted to the config file. Back up your config file to avoid losing access to encrypted snippets.
- **No network calls:** All processing is local. No data leaves your machine.

```bash
# Windows: use the full command name
snipcontext add "print('hello')" --title "Hello" --tag python
snipcontext search "hello world"
snipcontext list
snipcontext stats

# Or run via module
python -m snipcontext add "print('hello')" --title "Hello" --tag python
```

### Verify Installation

```bash
snipcontext --help          # or: python -m snipcontext --help
snipcontext providers       # List available export providers
```

### CLI Usage

```bash
# Add a snippet
snipcontext add "def authenticate(token):\n    return jwt.decode(token, SECRET)" \
  --title "JWT Authentication" \
  --desc "Decode and verify JWT tokens" \
  --lang python \
  --tag auth --tag jwt --tag security

# Search semantically
snipcontext search "how to validate auth tokens"

# Search by tag
snipcontext search "auth" --mode tag

# Export for Claude
snipcontext search "authentication" --provider claude --output context.xml

# List all snippets
snipcontext list

# Show stats
snipcontext stats

# Delete a snippet
snipcontext delete <snippet-id>

# Edit a snippet
snipcontext edit <snippet-id> --title "New Title" --add-tag python

# Rebuild search index
snipcontext build-index --force

# Watch for file changes and auto-reindex
snipcontext watch

# Run the demo
snipcontext demo
```

### Library Usage

```python
from snipcontext.core.models import Snippet, SnippetMetadata, Language
from snipcontext.core.storage import StorageEngine
from snipcontext.core.search import HybridSearch
from snipcontext.config.settings import get_config

# Initialize
config = get_config()
storage = StorageEngine(config)

# Create and save a snippet
snippet = Snippet(
    content="def memoize(fn):\n    cache = {}\n    ...",
    metadata=SnippetMetadata(
        title="Memoization Decorator",
        description="Cache function results",
        language=Language.PYTHON,
    ),
    tags=["python", "decorator", "performance"],
)
storage.save(snippet)

# Search with semantic understanding
searcher = HybridSearch(config)
searcher.index_snippets(storage.list_all())
results = searcher.search("cache function results decorator")

for r in results:
    print(f"{r.score:.3f} | {r.snippet.metadata.title}")
```

---

## 🔐 Encryption at Rest

SnipContext supports **Fernet (AES-128)** encryption for sensitive snippets. When enabled, snippet content is encrypted at rest using a key derived from a passphrase via PBKDF2 (100k iterations).

### Enable Encryption

```bash
# Enable encryption (required)
export SNIPCONTEXT_ENCRYPT_ENABLED=true

# Set passphrase (used for key derivation)
export SNIPCONTEXT_ENCRYPTION_PASSPHRASE="your-secure-passphrase"

# Optional: persist salt to config (auto-generated if omitted)
export SNIPCONTEXT_ENCRYPT_KEY_SALT="base64-encoded-salt"
```

### Encrypt Snippets

```bash
# Encrypt a new snippet
snipcontext add "api_key = 'sk-12345'" \
  --title "API Key" \
  --tag secret \
  --encrypt

# Mark as sensitive (auto-enables encryption)
snipcontext add "password = 'secret123'" \
  --title "DB Password" \
  --sensitive
```

### Decrypt for Viewing/Editing

```bash
# Decrypt for viewing
snipcontext decrypt <snippet-id>

# Encrypt an existing snippet
snipcontext encrypt <snippet-id>
```

> **Note:** When encrypted, the plaintext `content` is cleared from storage. The `encrypted_content` field stores the encrypted data. Use `snipcontext decrypt <id>` to restore plaintext for editing.

---

## 🔄 Index Rebuild & Resilience

SnipContext automatically detects and recovers from index corruption. The `HybridSearch` engine validates index integrity on load and rebuilds automatically when needed.

### Manual Rebuild

```bash
# Build or rebuild the semantic search index
snipcontext build-index

# Force rebuild (useful after corruption, dependency changes, or mode switches)
snipcontext build-index --force
```

### Auto-Recovery

The search engine automatically:

1. **Validates index integrity** on load (checks ID map lengths, matrix dimensions)
2. **Cleans up corrupted files** (deletes mismatched/corrupted index files)
3. **Falls back gracefully** — if semantic index unavailable, runs keyword-only search
4. **Rebuilds on demand** — `index_snippets()` auto-loads existing indices before rebuilding

### Watchdog / Real-time Indexing

Run `snipcontext watch` to monitor the snippets directory and automatically reindex when files change:

```bash
snipcontext watch
```

Disable via config if you prefer manual rebuilds only:

```bash
export SNIPCONTEXT_WATCHDOG_ENABLED=false
```

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│                  CLI (Typer + Rich)              │
├──────────┬──────────┬──────────┬────────────────┤
│  add     │  search  │  export  │  edit/delete   │
│  list    │  stats   │  watch   │  demo          │
└────┬─────┴────┬─────┴────┬─────┴───────┬────────┘
     │          │          │             │
     ▼          ▼          ▼             ▼
┌─────────────────────────────────────────────────┐
│              Search Engine (HybridSearch)        │
│  ┌──────────────┐  ┌──────────────────────────┐ │
│  │   Semantic    │  │       Keyword            │ │
│  │  FAISS Index  │  │     TF-IDF (sklearn)     │ │
│  └──────────────┘  └──────────────────────────┘ │
├─────────────────────────────────────────────────┤
│              Storage Engine                      │
│         Git-friendly JSON per snippet            │
├─────────────────────────────────────────────────┤
│              Data Models (Pydantic v2)           │
│     Snippet / SnippetMetadata / Language         │
└─────────────────────────────────────────────────┘
```

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for detailed design documentation.

---

## Configuration

SnipContext uses environment variables and a YAML config file:

```bash
# Use GPU for embeddings
export SNIPCONTEXT_EMBED_DEVICE="cuda"

# Change embedding model
export SNIPCONTEXT_EMBED_MODEL_NAME="all-mpnet-base-v2"

# Adjust search weights
export SNIPCONTEXT_SEARCH_SEMANTIC_WEIGHT="0.8"

# Enable auto-tagging
export SNIPCONTEXT_AUTO_TAG_ENABLED=true

# Enable deduplication
export SNIPCONTEXT_DEDUP_ENABLED=true
export SNIPCONTEXT_DEDUP_THRESHOLD="0.95"
```

Or edit `~/.config/SnipContext/snipcontext.yaml`:

```yaml
embedding:
  model_name: "all-MiniLM-L6-v2"
  device: "cpu"

search:
  default_mode: "hybrid"
  semantic_weight: 0.7
  keyword_weight: 0.3
  top_k: 10

auto_tag:
  enabled: true
  threshold: 0.75

dedup:
  enabled: true
  threshold: 0.95
```

---

## Development

```bash
# Clone
git clone https://github.com/billybox1926-jpg/snipcontext.git
cd snipcontext

# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=snipcontext

# Linting
ruff check .
mypy .

# Install pre-commit hooks
pre-commit install
```

---

## Roadmap

- [x] Core snippet CRUD with git-friendly storage
- [x] Semantic + hybrid search with local embeddings
- [x] LLM-optimized export providers (Claude, Cursor, OpenAI, Generic)
- [x] Rich CLI with Typer
- [x] Plugin system with entry points
- [x] Python library distribution (PyPI)
- [x] Auto-tagging and deduplication
- [x] Encryption at rest
- [x] File watchdog / real-time indexing
- [ ] Import from GitHub Gists
- [ ] Import from Git repositories
- [ ] Snippet templates and scaffolding
- [ ] Team sharing via git-sync
- [ ] VS Code extension

---

## Project Structure

```
snipcontext/
├── src/snipcontext/          # Python package
│   ├── __init__.py
│   ├── __main__.py           # python -m snipcontext
│   ├── cli/
│   │   └── main.py           # Typer CLI commands
│   ├── config/
│   │   └── settings.py       # Pydantic Settings
│   ├── core/
│   │   ├── models.py         # Pydantic data models
│   │   ├── storage.py        # Git-friendly JSON storage
│   │   ├── search.py         # Semantic + hybrid search
│   │   ├── auto_tag.py       # Embedding-based auto-tagging
│   │   └── watcher.py        # File watchdog
│   ├── plugins/
│   │   └── base.py           # Plugin base + manager
│   └── providers/
│       ├── base.py           # Provider interface
│       ├── claude.py         # Anthropic Claude XML
│       ├── cursor.py         # Cursor IDE format
│       ├── openai.py         # OpenAI format
│       └── generic.py        # Universal Markdown
├── tests/                    # Test suite
├── docs/                     # Documentation
│   ├── ARCHITECTURE.md
│   ├── API.md
│   └── MAINTAINER.md
├── pyproject.toml
├── CHANGELOG.md
└── README.md
```

---

## License & Contributing

MIT License — see [LICENSE](LICENSE) for details.

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) first. New contributors should check out our [Good First Issues](../../issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22).
