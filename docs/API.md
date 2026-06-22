# SnipContext Python API

The SnipContext library can be used programmatically in your own Python scripts and applications.

## Quick Start

```python
from snipcontext.core.models import Snippet, SnippetMetadata, Language
from snipcontext.core.storage import StorageEngine
from snipcontext.core.search import HybridSearch
from snipcontext.config.settings import get_config

# Initialize
config = get_config()
storage = StorageEngine(config)

# Create a snippet
snippet = Snippet(
    content="def fibonacci(n):\n    return n if n < 2 else fibonacci(n-1) + fibonacci(n-2)",
    metadata=SnippetMetadata(
        title="Fibonacci Sequence",
        description="Classic recursive fibonacci",
        language=Language.PYTHON,
    ),
    tags=["python", "recursion", "math"],
)

# Save it
storage.save(snippet)

# Search
searcher = HybridSearch(config)
searcher.index_snippets(storage.list_all())
results = searcher.search("recursive math function", top_k=5)

for r in results:
    print(f"{r.score:.3f} | {r.snippet.metadata.title}")
```

## Snippet Model

### Creating Snippets

```python
from snipcontext.core.models import Snippet, SnippetMetadata, Language

# Minimal snippet
s1 = Snippet(
    content="print('hello')",
    metadata=SnippetMetadata(title="Hello World"),
)

# Full snippet
s2 = Snippet(
    content="async def fetch(url):\n    return await aiohttp.get(url)",
    metadata=SnippetMetadata(
        title="Async HTTP Fetch",
        description="Fetch a URL asynchronously using aiohttp",
        language=Language.PYTHON,
        source_url="https://docs.aiohttp.org",
        framework="aiohttp",
        version="3.x",
        author="Your Name",
        confidence="production",
        llm_optimized=True,
        custom_tags={"category": "networking", "async": True},
    ),
    tags=["python", "async", "http", "aiohttp"],
)
```

### Versioning

```python
# Create a version snapshot before editing
snippet.bump_version("Before refactoring")

# Make changes
snippet.content = "def new_improved(): ..."
snippet.metadata.confidence = "production"
snippet.touch()

# Save
storage.save(snippet)

# Access version history
for v in snippet.versions:
    print(f"{v.created_at}: {v.change_message}")
    print(v.content[:100])  # Previous content
```

### Tag Management

```python
# Tags are auto-normalized (lowercase, deduped, sorted)
snippet = Snippet(
    content="x",
    metadata=SnippetMetadata(title="T"),
    tags=["Python", " AUTH ", "python", "web"],  # Will become ["auth", "python", "web"]
)

# Merge additional tags
snippet.merge_tags(["security", "jwt"])

# Access
print(snippet.tags)        # ['auth', 'jwt', 'python', 'security', 'web']
print(snippet.tag_line)    # #auth, #jwt, #python, #security, #web
```

## Storage Engine

### CRUD Operations

```python
from snipcontext.core.storage import StorageEngine, SnippetNotFoundError

storage = StorageEngine(config)

# Create / Update
storage.save(snippet)

# Read
try:
    loaded = storage.get(snippet.id)
except SnippetNotFoundError:
    print("Snippet not found")

# Delete
storage.delete(snippet.id)

# Check existence
if storage.exists(snippet.id):
    print("Found!")
```

### Bulk Operations

```python
# Iterate all snippets
for snippet in storage.iter_all():
    print(snippet.metadata.title)

# Get all as list
all_snippets = storage.list_all()

# Count
total = storage.count()

# Find by tag
auth_snippets = storage.find_by_tag("authentication")

# Get all tags
tags = storage.get_all_tags()

# Statistics
stats = storage.get_stats()
print(f"Total: {stats['total_snippets']}")
print(f"Languages: {stats['languages']}")
```

### Import / Export

```python
# Export all snippets to a single JSON file
storage.export_all(Path("./backup.json"))

# Import from JSON
storage.import_file(Path("./backup.json"))
```

## Search Engine

### Building the Index

```python
from snipcontext.core.search import HybridSearch

searcher = HybridSearch(config)

# Build from all stored snippets
snippets = storage.list_all()
searcher.index_snippets(snippets)

# Save index to disk
# (automatically called by index_snippets)

# Load existing index on startup
loaded = searcher.load_indices()
if not loaded:
    searcher.index_snippets(storage.list_all())
```

### Search Modes

```python
from snipcontext.core.models import SearchMode

# Hybrid (default) — best of both worlds
results = searcher.search("authentication middleware", mode=SearchMode.HYBRID)

# Pure semantic search
results = searcher.search("handle user login", mode=SearchMode.SEMANTIC)

# Pure keyword search
results = searcher.search("def authenticate jwt", mode=SearchMode.KEYWORD)

# Tag search (exact match)
results = searcher.search("auth", mode=SearchMode.TAG)
```

### Search Results

```python
results = searcher.search("database connection", top_k=10)

for result in results:
    print(f"Score: {result.score:.3f}")
    print(f"Matched by: {result.matched_by}")  # semantic, keyword, hybrid, or tag
    print(f"Title: {result.snippet.metadata.title}")
    print(f"Code:\n{result.snippet.content[:200]}")
    print("---")
```

## Export Providers

### Using Providers

```python
from snipcontext.plugins.base import PluginManager

pm = PluginManager()
pm.load_builtin_providers()

# Get a provider
claude = pm.get_provider("claude")
generic = pm.get_provider("generic")

# Export single snippet
output = claude.export_single(snippet)
print(output)

# Export multiple snippets
batch = generic.export_batch(
    [snippet1, snippet2, snippet3],
    title="Authentication Layer",
)
```

### Available Providers

| Provider | Format | Best For |
|----------|--------|----------|
| `generic` | Markdown | Universal compatibility |
| `claude` | XML | Anthropic Claude |
| `cursor` | Markdown with file headers | Cursor IDE |
| `openai` | Markdown with dividers | ChatGPT / OpenAI |

All providers include snippet metadata by default (`include_metadata=True`):
`title`, `description`, `language`, `tags`, `framework`, `version`, `source_url`, `author`, `confidence`, and `llm_optimized`.

Set `include_metadata=False` to export code only.

### Creating Custom Providers

```python
from snipcontext.providers.base import BaseProvider, ExportFormat

class MyProvider(BaseProvider):
    name = "myprovider"
    description = "Custom format for my use case"
    format = ExportFormat.MARKDOWN

    def export_single(self, snippet):
        return f"""
# {snippet.metadata.title}
## Meta
Language: {snippet.metadata.language.value}
Tags: {snippet.tag_line}
## Code
```{snippet.metadata.language.value}
{snippet.content}
```
"""

# Register via entry points or use directly
```

## Configuration

### Programmatic Configuration

```python
from snipcontext.config.settings import Config, EmbeddingConfig

config = Config(
    embedding=EmbeddingConfig(
        model_name="all-mpnet-base-v2",  # Higher quality, slower
        device="cuda",                    # Use GPU
        batch_size=64,
    ),
)

storage = StorageEngine(config)
searcher = HybridSearch(config)
```

### Environment Variables

```bash
# Use a different embedding model
export SNIPCONTEXT_EMBED_MODEL_NAME="all-mpnet-base-v2"

# Use GPU for embeddings
export SNIPCONTEXT_EMBED_DEVICE="cuda"

# Change default search weights
export SNIPCONTEXT_SEARCH_SEMANTIC_WEIGHT="0.8"
export SNIPCONTEXT_SEARCH_KEYWORD_WEIGHT="0.2"

# Change data directory
export SNIPCONTEXT_STORAGE_DATA_DIR="/mnt/snipcontext"
```

## Error Handling

```python
from snipcontext.core.storage import SnippetNotFoundError, StorageError
from pydantic import ValidationError

try:
    snippet = storage.get("nonexistent")
except SnippetNotFoundError:
    # Handle missing snippet
    pass

try:
    bad_snippet = Snippet(content="", metadata=SnippetMetadata(title=""))
except ValidationError as e:
    # Handle validation errors
    print(e.errors())
```
