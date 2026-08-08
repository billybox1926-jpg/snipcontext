# Configuration

SnipContext resolves its storage location using a discovery hierarchy. This document explains the order of precedence and how to customize it for your environment.

## Discovery Hierarchy

When SnipContext needs to read or write data, it resolves the **storage root** in this order:

1. **`SNIPCONTEXT_HOME` environment variable** — explicit override  
2. **`.snipcontext/` in the current directory or nearest ancestor** — project-local mode  
3. **Platform-appropriate user data directory** — global fallback

If `SNIPCONTEXT_HOME` is set, it takes precedence over everything else. This is useful for CI/CD pipelines or when you want to keep all data in a custom location.

If neither an env var nor an explicit flag is provided, SnipContext walks up from the current working directory looking for a `.snipcontext/` directory. If found, it uses that directory as the storage root. Otherwise it falls back to the platform-appropriate global location:

- **Windows:** `%LOCALAPPDATA%\SnipContext`
- **macOS:** `~/Library/Application Support/SnipContext`
- **Linux:** `~/.local/share/snapshot` (via `platformdirs`)

## Project-Local Mode

Project-local mode is **opt-in**. Run the following command from your repository root:

```bash
sc init --local
```

This scaffolds a `.snipcontext/` directory with:

```text
.snipcontext/
├── config.yaml          # Project-specific settings
├── snippets/            # Snippet storage (one JSON file per snippet)
├── index.faiss          # Search index (binary, gitignored)
└── .gitignore           # Auto-generated to ignore index.faiss
```

Once initialized, any SnipContext command run from inside the project (or a subdirectory) automatically uses the local collection.

You can customize the target directory name:

```bash
sc init --local --path ./my-snippets
```

> **Note:** The target directory must not already exist. If you need to reinitialize, remove the existing directory first.

## Inspecting Configuration

Use `sc info` to see the current storage mode and resolved paths:

```bash
sc info
```

Output:

```text
SnipContext Configuration
+-------------------------------------------------------------+
| Setting      | Value                                      |
|--------------+--------------------------------------------|
| Mode         | project-local                              |
| Storage root | /home/user/projects/myapp/.snipcontext/    |
| Snippets dir | /home/user/projects/myapp/.snipcontext/... |
| Index dir    | /home/user/projects/myapp/.snipcontext/... |
| Config file  | /home/user/projects/myapp/.snipcontext/... |
+-------------------------------------------------------------+
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `SNIPCONTEXT_HOME` | Override the storage root entirely |
| `SNIPCONTEXT_STORAGE__DATA_DIR` | Override only the data directory |
| `SNIPCONTEXT_STORAGE__SNIPPETS_DIR` | Override the snippets subdirectory |
| `SNIPCONTEXT_STORAGE__INDEX_DIR` | Override the index subdirectory |


## Auto-Tagging

SnipContext can suggest tags for new snippets by finding semantically similar
existing snippets via the FAISS index.

| Variable | Default | Description |
|----------|---------|-------------|
| `SC_AUTO_TAG_ENABLED` | `true` | Enable auto-tag suggestions on `sc add` |
| `SC_AUTO_TAG_TOP_K` | `5` | Number of similar snippets to consider |
| `SC_AUTO_TAG_MIN_FREQUENCY` | `2` | Minimum tag frequency among neighbors to suggest it |
| `SC_AUTO_TAG_AUTO_ACCEPT` | `false` | Automatically apply suggested tags without prompting |

Or via YAML config:

```yaml
auto_tag:
  enabled: true
  top_k: 5
  min_frequency: 2
  auto_accept: false
```

## Search Weighting

The hybrid search mode fuses semantic and keyword scores. You can tune the balance globally or per query.

| Variable | Default | Description |
|----------|---------|-------------|
| `SNIPCONTEXT_SEARCH_SEMANTIC_WEIGHT` | `0.7` | Semantic fusion weight in hybrid mode |
| `SNIPCONTEXT_SEARCH_KEYWORD_WEIGHT` | `0.3` | Keyword fusion weight in hybrid mode |

Or via YAML config:

```yaml
search:
  default_mode: hybrid
  semantic_weight: 0.7
  keyword_weight: 0.3
  top_k: 10
  min_score: 0.1
```

Per-query overrides are available on the CLI:

```bash
snipcontext search "auth token" --semantic-weight 0.9
snipcontext search "jwt" --keyword-weight 0.8
```

If only one weight is provided, the other is derived as `1 - provided_weight`.

> **Requirement:** Install the `[semantic]` extra: `pip install snipcontext[semantic]`.

## File Watcher

SnipContext's `sc watch` command uses the file watcher integration to keep the
search index in sync with disk changes. You can tune its behavior with these
storage settings:

| Variable | Default | Description |
|----------|---------|-------------|
| `SNIPCONTEXT_STORAGE__WATCHDOG_ENABLED` | `true` | Enable the file watcher auto-index |
| `SNIPCONTEXT_STORAGE__WATCHDOG_DEBOUNCE_SECONDS` | `2.0` | Debounce window (seconds) — batches rapid changes into a single reindex |
| `SNIPCONTEXT_STORAGE__WATCHDOG_POLL_INTERVAL` | `5.0` | Poll interval (seconds); present in config schema but the current watcher uses `watchdog.Observer` rather than polling |

Or via YAML config:

```yaml
storage:
  watchdog_enabled: true
  watchdog_debounce_seconds: 2.0
  watchdog_poll_interval: 5.0
```

For a full list of configurable keys, run:

```bash
sc config list
```

## Configuration File Format

When `sc init --local` creates a `.snipcontext/config.yaml`, it serializes the current `Config` object. The file uses standard YAML and matches the structure of SnipContext's internal settings:

```yaml
storage:
  data_dir: /absolute/path/to/.snipcontext
  snippets_dir: snippets
  index_dir: index
  auto_commit: true
search:
  default_mode: hybrid
  top_k: 10
```

Changes to `config.yaml` are picked up by SnipContext automatically. If a setting is also present in an environment variable, the environment variable takes precedence.

## Migration

If you already have snippets in the global location and want to move them into a project-local `.snipcontext/`, do so manually:

```bash
sc init --local
cp -r ~/.local/share/snapshot/snippets/* .snipcontext/snippets/
sc index rebuild  # Rebuild the search index
```

There is no automatic migration to prevent accidental data loss between independent collections.
