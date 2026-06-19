# SnipContext

[![PyPI version](https://img.shields.io/pypi/v/snipcontext)](https://pypi.org/project/snipcontext/)
[![CI Status](https://img.shields.io/github/actions/status/billybox1926-jpg/snipcontext/ci)](https://github.com/billybox1926-jpg/snipcontext/actions/workflows/ci.yml)
[![License](https://img.shields.io/github/license/billybox1926-jpg/snipcontext)](LICENSE)
[![Python](https://img.shields.io/pypi/pyversions/snipcontext)](https://pypi.org/project/snipcontext/)
[![Downloads](https://img.shields.io/pypi/dm/snipcontext)](https://pypi.org/project/snipcontext/)

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

| Feature | Status |
|---------|--------|
| Rich snippet saving with tags, metadata, and versioning | ✅ |
| **Semantic search** with local embeddings (sentence-transformers + FAISS) | ✅ |
| **Hybrid search** — semantic + keyword with configurable weights | ✅ |
| One-command export optimized for major LLMs | ✅ |
| CLI + Library support (Python) | ✅ |
| Plugin system for new providers and exporters | ✅ |
| Git-friendly, local-first storage | ✅ |
| Import/export for backup and sharing | ✅ |

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
# From PyPI (recommended)
pip install snipcontext

# Or with uv
uv tool install snipcontext

# From source (after cloning)
pip install -e ".[dev]"

# Or install directly from GitHub
pip install git+https://github.com/billybox1926-jpg/snipcontext.git
```

#### Windows Users: Use `snipcontext` instead of `sc`

Windows has a built-in `sc.exe` (Service Control) that shadows the `sc` CLI entry point. Use the full command name instead:

```bash
snipcontext add "print('hello')" --title "Hello" --tag python
snipcontext search "hello world"
snipcontext list
snipcontext stats
```

Or run via module:

```bash
python -m snipcontext add "print('hello')" --title "Hello" --tag python
```

#### Verify Installation

```bash
snipcontext --help          # or: python -m snipcontext --help
snipcontext providers       # List available export providers
```

### CLI Usage

> **Note:** On Windows, use `snipcontext` instead of `sc` (see [Installation](#installation)).

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

> **Note:** When encrypted, the plaintext `content` is cleared from storage. The `encrypted_content` field stores the encrypted data. Use `sc decrypt <id>` to restore plaintext for editing.

---

## 🔄 Index Rebuild & Resilience

SnipContext automatically detects and recovers from index corruption. The `HybridSearch` engine validates index integrity on load and rebuilds automatically when needed.

### Manual Rebuild

```bash
# Check if rebuild is needed (skips if index is valid)
snipcontext rebuild-index

# Force rebuild (useful after corruption, dependency changes, or mode switches)
snipcontext rebuild-index --force
```

### Auto-Recovery

The search engine automatically:
1. **Validates index integrity** on load (checks ID map lengths, matrix dimensions)
2. **Cleans up corrupted files** (deletes mismatched/corrupted index files)
3. **Falls back gracefully** — if semantic index unavailable, runs keyword-only search
4. **Rebuilds on demand** — `index_snippets()` auto-loads existing indices before rebuilding

---

## Architecture

```
CLI (Typer + Rich)
  │
├── Providers (Claude XML / Cursor / OpenAI / Generic Markdown)
│
├── Search Engine
│   ├── Semantic: sentence-transformers + FAISS
│   ├── Keyword: TF-IDF (scikit-learn)
│   └── Hybrid: configurable weighted fusion
│
├── Storage Engine
│   └── Git-friendly JSON files per snippet
│
└── Data Models (Pydantic v2)
    └── Snippet / SnippetMetadata / SnippetVersion
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
- [ ] Real-time index updates (currently requires rebuild)
- [ ] Import from GitHub Gists
- [ ] Import from Git repositories
- [ ] Snippet templates and scaffolding
- [ ] Team sharing via git-sync
- [ ] VS Code extension

---

## Project Structure

```
snipcontext/
├── snipcontext/              # Python package
│   ├── __init__.py           # Package exports
│   ├── __main__.py           # python -m snipcontext
│   ├── core/                 # Core engine (models, storage, search)
│   │   ├── models.py         # Pydantic data models
│   │   ├── storage.py        # Git-friendly JSON storage
│   │   └── search.py         # Semantic + hybrid search
│   ├── providers/            # LLM export providers
│   │   ├── base.py           # Provider interface
│   │   ├── claude.py         # Anthropic Claude XML
│   │   ├── cursor.py         # Cursor IDE format
│   │   ├── openai.py         # OpenAI format
│   │   └── generic.py        # Universal Markdown
│   ├── plugins/              # Plugin system
│   │   └── base.py           # Plugin base + manager
│   ├── config/               # Configuration
│   │   └── settings.py       # Pydantic Settings
│   └── cli/                  # Command-line interface
│       └── main.py           # Typer CLI commands
├── tests/                    # Comprehensive test suite
├── docs/                     # Documentation
│   ├── ARCHITECTURE.md       # Design docs
│   ├── API.md                # Python API reference
│   └── MAINTAINER.md         # Maintainer guide
├── pyproject.toml            # Modern Python packaging
└── README.md                 # This file
```

---

## License

MIT License — see [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) first. New contributors should check out our [Good First Issues](../../issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22).
