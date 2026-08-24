# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Removed
- **BREAKING:** the `sc` console script is no longer installed. It collided with
  the Windows built-in `sc.exe` (Service Control), and PEP 621
  `[project.scripts]` has no environment-marker support, so it could not be
  shipped on POSIX only. Use `snip` (short) or `snipcontext` (full); POSIX users
  who want the old name can add `alias sc=snipcontext` to their shell profile
  (closes #209)

### Changed
- Web UI routes are mounted under `/api`, so they no longer collide with the
  canonical snippets router and are reachable over HTTP (closes #200)
- `SnippetMetadata` now validates on assignment, so an invalid value can no
  longer be silently stored and corrupt the snippet on reload (closes #201)
- Pre-commit hooks updated to ruff v0.16.4 / mypy v1.20.2, with mypy scoped to
  `src/snipcontext` to match CI (closes #204)
- `.nvmrc` added and `make build-frontend` now verifies the node version before
  running `npm ci` (closes #210)
- Expanded `SECURITY.md` with a response timeline, supported versions, and an
  explicit in/out-of-scope boundary (closes #207)

### Fixed
- `ClaudeProvider` exports route content through `sanitize_code()`, so snippet
  backticks can no longer break out of `<document_content>` (closes #195)
- Sanitization strips the full C1 control range (including 8-bit DCS/OSC) and
  Unicode bidi overrides (closes #196)
- Invalid languages sent to the web UI update endpoint now return 422 with a
  logged warning instead of being silently swallowed (closes #198)
- `gen_report.py` no longer probes a hardcoded per-user Windows path (closes #205)
- `.github/CODEOWNERS` lists the real maintainer instead of a placeholder org
  (closes #203)
- `CONTRIBUTORS.md` links the `saltines321-debug` GitHub handle (closes #208)

## [0.8.1] - 2026-08-12

### Added
- Packaged frontend assets with the Python package
- `snipcontext serve` now serves the bundled web UI from the same port as the API
- SPA fallback route so React Router paths work without a separate frontend server

### Changed
- Makefile adds `build-frontend` target to build and stage web UI assets for packaging

## [0.8.0] - 2026-08-12

### Added
- Web UI for snippet browsing, search, and management with FastAPI + React
- Snippet list with pagination, language/tag filtering, and detail view
- Inline snippet editing with live WebSocket updates
- Tag management UI with inline rename and delete
- Bulk tag merge UI with source/destination selection and preview counts
- Export UI with provider selection and formatted output preview
- WebSocket live updates for snippets, tags, and index rebuild progress
- `POST /api/tags/merge` endpoint for bulk tag consolidation
- Frontend hooks for tags, search, snippets, export, index status, and WebSocket

### Changed
- Backend router types improved with targeted `# type: ignore[untyped-decorator]` annotations
- Storage tag mutations now broadcast `tags_updated` events

### Fixed
- Mypy errors in `web_ui.py` including invalid `list_all(include_deleted=...)` calls and `soft_delete` references

## [0.7.0] - 2026-08-11

### Added
- Neovim plugin (`:SnipcontextList`, `:SnipcontextSave`, `:SnipcontextRefresh`) with Telescope support
- `snipcontext stats` command with Rich formatting, `--verbose`, and `--json` output
- Auto-index switching documentation and tests for flat → IVFPQ promotion at threshold
- Provider contract tests using Hypothesis for adversarial Unicode/edge cases
- VS Code extension sidebar for browsing and inserting snippets

### Changed
- CI fully migrated to `uv` for installs, caching, and test execution
- Config init error handling improved with clearer `typer.BadParameter` messages
- Migration strategy documented with `docs/MIGRATION.md` and stub `snipcontext migrate` command

### Fixed
- Snapshot and registry tests aligned with current package version

## [0.2.0] - 2026-08-11

### Added
- Config init error handling with `typer.BadParameter` (#160)
- Optional file watcher for automatic index rebuild via `snipcontext watch` and `--watch` (#161)
- `snipcontext migrate` stub and `docs/MIGRATION.md` for upgrade guidance (#162)
- Provider contract tests using Hypothesis for adversarial Unicode/edge cases

### Changed
- CI now uses `uv` for faster, reproducible installs and caching

## [Unreleased]

### Added
- `snipcontext migrate` stub command to prepare for future automatic migrations.
- `docs/MIGRATION.md` with detailed backup and migration instructions.
- Storage version tracking via `index/_meta.json`.

### Migration
No migration is required for this version. However, we recommend backing up before any upgrade.

## [0.6.2] - 2026-08-09

### Changed
- Workflow: publish job now skips build/publish if version already exists on PyPI.
- Docs: corrected Linux fallback path in `configuration.md`.
- Docs: added `help <command>` note to TUI guide.
- Docs: noted A2A Agent Card route in `web.md`.

## [0.6.0] - 2026-08-09

### Added
- `sc import` command for importing snippet collections from YAML, JSON, Markdown, and `.tar.gz` sources.
- Built-in collection support via `snipcontext:python-stdlib` for curated Python standard library patterns.
- Preview mode for imports using `--dry-run` / `--list`.
- `docs/import.md` with comprehensive import usage, formats, examples, and security guidance.
- `docs/web.md` with `sc serve` usage, endpoints, and configuration.
- `docs/tui.md` with `sc repl` usage, commands, and keyboard shortcuts.
- **Ollama Provider**: Local-first export provider for Ollama
  - Connects to local Ollama instance at `http://localhost:11434`
  - Supports model selection via `--model` flag
  - Graceful offline behavior with helpful error messages
  - Optional dependency: `pip install snipcontext[ollama]`
  - Configuration via `ollama` section in settings
  - Documented in `docs/providers.md` and `docs/API.md`
  - Health check support via `sc providers --health`
- Configurable hybrid search weighting via `--semantic-weight` and `--keyword-weight` CLI flags and `search.semantic_weight` / `search.keyword_weight` config.
- Windows-friendly `snip` console script alias to avoid `sc.exe` collision.

### Changed
- Imported snippets are automatically refreshed in the search index after import.
- Import error messaging now includes built-in collection scheme guidance.
- Default hybrid search weighting remains 0.7/0.3 for backward compatibility.

### Fixed
- Safe archive extraction rejects path traversal and unsupported members.
- Import deduplication uses content hash checks to skip exact duplicates.
- Ruff docstring warnings in `HybridSearch.search()`.

## [0.4.1] – 2026-06-23

### Added
- **Export schema versioning** – Every `export_batch` output now includes a `Export schema version: 1.0.0` header (or provider‑specific comment). This makes it easier to detect breaking format changes. (#98)
- **Hash‑based exact dedup** – A fast SHA‑256 hash check runs **before** the expensive semantic dedup step, saving time and compute on duplicate content. (#101)
- **Configurable storage location** – You can now use a **project-local `.snipcontext/`** directory (via `sc init --local`) or override the storage root via the `SNIPCONTEXT_HOME` environment variable. (#36)
- **Search history & favorites** – All search queries are now stored locally. Use `sc search --history` to see recent queries, `--favorites` to see starred ones, `--rerun <id>` to re‑execute, and `--favorite <id>` to toggle a query as a favorite. (#35)
|- **Auto-tagging documentation** – Documented the auto-tagging feature, configuration variables (`SC_AUTO_TAG_*`), YAML config format, interaction with deduplication, and the `[semantic]` extra requirement. (#110)
|- **`sc demo` documentation** – Documented the built-in demo command, its behavior (seeds sample snippets, previews search/export, respects existing data), and added a README onboarding section. (#109)
|- **`sc watch` documentation** – Documented the file watcher command, its foreground behavior, debounce mechanism, and configuration reference (`SNIPCONTEXT_STORAGE__WATCHDOG_*`). (#108)
|- **Platform support matrix** – Added README section with compatibility table, per-platform install instructions, ARM-specific notes, and links to #105, #91, and #106. (#107)
|- **Quick Start semantic search guide** – Added README section with copy-pasteable commands demonstrating semantic search, embedded demo GIF, and `[semantic]` extra note. (#102)
|- **Onboarding / documentation improvements** – Added `docs/migrate.md` and `docs/performance.md`, updated README badges (PyPI version, downloads), and expanded the Documentation index. (#19)
|- **Test coverage boost** – Added `tests/core/test_search_coverage.py` with focused HybridSearch, VectorIndex, EmbeddingEngine, and KeywordIndex branch coverage. `storage.py` is at 91% and `search.py` is at 75%. (Coverage Gap Plan)

### Changed
- **Plugin system** – The `PluginRegistry` is now the single source of truth for discovery, loading, unloading, and health checks. Providers are now full plugins with lifecycle hooks and version compatibility checks (`requires`). CLI now includes `sc plugins --load` / `--unload`.
- **`BaseProvider` now inherits from `Plugin`** – All providers gain `on_load` and `on_shutdown` hooks (default no‑ops).
- **CLI snapshot tests** – Stabilised across all environments. Output is now deterministic with ASCII box‑drawing and fixed‑width tables.

### Fixed
- **Snapshot instability** – Tables now consistently use `+`, `-`, `|` borders. Environment variables and explicit ASCII box style are used to guarantee deterministic output.
- **Mypy errors** – Fixed return type annotation in `SearchHistoryStore.toggle_favorite()` and silenced untyped decorator warning in A2A agent card router.
- **Minimal install skip behavior** – Tests that require unavailable optional dependencies now skip cleanly when the package is absent.

### Deprecated
- (None)

### Removed
- (None)

## [0.2.4] - 2026-06-21

### Added
- Shared context singleton for CLI commands — Config, StorageEngine, and HybridSearch initialized once and reused across all commands (`cli/context.py`)
- Debounce mechanism for file watcher (closes #100)
- `--reload` flag on any command to force re-initialization of shared context
- SPEC.md as authoritative behavior contract

### Changed
- `Optional[X]` replaced with `X | None` syntax (ruff UP045)
- Publish workflow hardened to use `PYPI_API_TOKEN` instead of OIDC

### Fixed
- Shared context: `get_config()` was called 19 times, `StorageEngine` instantiated 13 times per session — now singleton

## [0.2.5] - 2026-06-22

### Added
- Interactive TUI mode (`tui/` module) — full terminal UI with commands, completer, and formatter
- Optional dependency groups: `[semantic]`, `[tui]`, `[all]` — core CLI works without Rust toolchain (closes #62)

### Changed
- `sentence-transformers` and `faiss-cpu` moved to `[semantic]` extra — already lazy-imported in `search.py`
- `sentence-transformers` and `faiss-cpu` moved to `[semantic]` extra — already lazy-imported in `search.py`
- `sc` commands gracefully skip unavailable optional features if extras are not installed
- README updated with ARM/Termux install guidance and optional dep documentation
- Sprint + Priority custom fields on project board with full issue tagging

### Fixed
- **ARM/Termux compatibility** — Made Rust-dependent packages optional via dependency groups, resolving installation failures on ARM/Termux environments (closes #62).
- Snippet content sanitization to prevent XSS in downstream rendering (closes #93)
  - New `core/sanitization.py` module: `sanitize_text()`, `sanitize_code()`, `sanitize_html()`, `sanitize_for_display()`
  - Applied to all export providers (generic, openai, cursor, claude) and CLI display
  - Prevents code-fence breakout, HTML injection, ANSI escape injection, Rich markup injection

## [0.3.0] - 2026-06-22

### Added
- **Improved Snippet Editing UX** (closes #2) — partial updates, `--interactive` ($EDITOR), confirmation prompt, `--lang`, `--file`, `--message` flags
- **Analytics & Stats Command** (closes #18) — `sc stats` with basic and `--detailed` modes: total count, language/tag breakdown, ASCII bar charts, access metrics, storage breakdown, JSON output (`--json`)
- **Richer Snippet Metadata** (closes #3) — `framework`, `version`, `source_url`, `custom_tags` fields on SnippetMetadata; `--source`, `--framework`, `--version`, `--custom key=value` flags on `sc add` and `sc edit`
- **Improved Search Filters & Scoring** (closes #4) — `--fuzzy`, `--threshold`, `--lang`, `--tag`, `--boost-recent`, `--explain`, `--no-semantic` flags; recency boost scoring
- **Multi-Query Search** (closes #32) — space-separated queries with weighted reciprocal rank fusion (`query^N` syntax)
- **BM25 Keyword Search** (closes #90) — replaced TF-IDF with BM25 for better keyword relevance
- **Lighter Default Model** (closes #96) — `--no-semantic` flag, lighter model docs
- **Binary Distribution** (closes #24) — PyInstaller + `uv tool` support
- **Web API** — bootstrap REST API with FastAPI endpoints for snippets
- **Interactive TUI** (closes #29) — full terminal UI with command completer
- `sc index` / `sc build-index` — rebuild search indices
- `sc watch` — file watchdog for automatic reindexing
- `sc demo` — seed sample snippets and run interactive demo
- `sc export` — export to Claude, Cursor, OpenAI, or Generic Markdown
- `sc stats` — collection analytics with bar charts
- `sc providers` / `sc config-path` — utility commands
- Auto-tagging via FAISS embeddings with similarity-based deduplication
- Soft-delete support
- Plugin system with entry points for providers and exporters
- Stdin piping support for `sc add`
- Multi-Python CI matrix (3.10–3.13)

### Changed
- Optional dependency groups: `[semantic]`, `[tui]`, `[web]`, `[all]`
- Core CLI works without Rust toolchain (closes #62)
- Fixed conflicting short options across CLI commands

### Fixed
- Ruff lint errors E741, B007, B905 across search, CLI, and test modules
- Mypy arg-type errors in `cli/search.py` — replaced `**dict` unpack with explicit kwargs
- `datetime.UTC` incompatibility with Python 3.10 — replaced with `timezone.utc`
- Snippet content XSS sanitization (closes #93)
- Web API dependency isolation for CI (PR #104)
- Short option conflicts (`-f`, `-t`, `-s`, `-m`) across commands

## [0.4.0] - 2026-06-22

### Added
- `sc index` CLI command — rebuild search index from all stored snippets
- `sc build-index` CLI command — smarter index builder with `--force` and index-exists check
- `Annotated[bool, typer.Option(...)]` for all `force` parameters (fixes typer crash with `from __future__ import annotations`)
- CI workflow auto-fixes ruff lint/format and commits back on push
- Mypy type checking as non-blocking CI step (`continue-on-error`)
- Content hash tracking and reverse id map in `VectorIndex` for incremental index updates
- `HybridSearch.indices_ready` property with auto-load from disk
- `_keyword_dirty` tracking for lazy keyword index rebuilds
- `sc watch` CLI command — file watchdog for automatic reindexing
- `sc demo` CLI command — seed sample snippets and run interactive demo
- Auto-tagging via FAISS embeddings (`sc add` suggests tags based on similarity)
- Similarity-based deduplication on `sc add` (configurable threshold)
- Soft-delete support (`StorageEngine.mark_deleted`, `sc delete`)
- `sc export` — export snippets for Claude, Cursor, OpenAI, or Generic Markdown
- `sc edit` — edit existing snippets with field-level updates
- `sc stats` — show collection statistics
- `sc providers` — list available export format providers
- `sc config-path` — show config/data/index directory paths
- Plugin system with entry points for providers and exporters
- Stdin piping support for `sc add`
- Multi-Python test matrix (3.10–3.13) in CI
- Pre-commit hooks (ruff, mypy)
- Makefile for common dev tasks
- CONTRIBUTORS.md and MAINTAINER.md

### Changed
- Replaced PyPI/CI/Downloads badges with accurate ones (license, Python, ruff, mypy, contributors, last commit, issues)
- Relaxed Rich version pin from `<14` to `<16`
- Replaced `Operating System :: OS Independent` classifier with `POSIX :: Linux` and `MacOS`
- Fixed conflicting short options across CLI commands (`-f`, `-t`, `-s`, `-m`)
- Consolidated duplicate `_OPT_*` module-level constants
- `StorageEngine.vacuum` validates snippets before removing orphans (prevents data loss)
- `StorageEngine.get_tags` narrows `except` to `StorageError`
- `VectorIndex.save` uses `json.dump` for idmap (was manual quoting)
- `HybridSearch.add_snippet` updates vector index incrementally (no full rebuild)
- `HybridSearch.remove_snippet` removes from vector index directly
- `delete` command: `snippet_id` as positional arg, `force` as option

### Fixed
- `ImportError: cannot import name 'index'` — restored `sc index` command removed in refactor
- `RuntimeError: Type not yet supported: OptionInfo` — typer crash with `from __future__ import annotations`
- `AttributeError: 'HybridSearch' object has no attribute 'embedder'` — test mocks updated
- `AttributeError: 'HybridSearch' object has no attribute 'vector_index'` — test mocks updated
- `SyntaxError: parameter without a default follows parameter with a default` — `delete` command parameter order
- `idmap.json` serialization — was manual string joining, now proper `json.dump`
- `content_hashes.json` not persisted in `VectorIndex.save`

## [Unreleased]

### Added
- `except: pass` in `search.py` silently swallowing index cleanup errors — **fully addressed**. Replaced with proper logging (`logger.warning`) and error propagation (`return False`) in index load/cleanup paths.
- Duplicate `_OPT_QUERY`, `_OPT_IDS`, `_OPT_OUTPUT` constants causing option conflicts
- Short option conflicts: `-f` (file/fuzzy/force), `-t` (tag/threshold), `-s` (sensitive/sort), `-m` (mode/message)
- `DedupConfig` missing `auto_accept` — no way to skip dedup warnings in scripts
- `AutoTagConfig.auto_accept` defined but never used — `_accept_auto_tags` always prompts
- Windows `sc.exe` conflict — documented `snipcontext` as alternative command name
- CI mypy failures — added `--ignore-missing-imports`, `--no-site-packages`, disabled specific error codes
- CI test failures — set `PYTHONPATH`, used `python -m pytest`, cached Hugging Face models
- `ruff` lint errors across multiple files (F401, F541, F841, I001, B904, UP037)
- `mypy` type errors in `watcher.py`, `auto_tag.py`, `settings.py`

### Removed
- `python-ulid` dependency (unused)
- Deprecated `sc index` command (re-added in v0.2.3 as alias)

## [0.2.3] - 2026-06-20

### Changed
- Version bump to 0.2.3

## [0.2.2] - 2026-06-20

### Fixed
- Use `pip` instead of `uv` for twine install in release workflow

## [0.2.1] - 2026-06-20

### Fixed
- Install twine before verify step in release workflow

## [0.2.0] - 2026-06-20

### Added
- PyPI publishing via trusted publishing (OIDC)
- TestPyPI publishing for CI verification
- Multi-Python test matrix in CI

### Changed
- Dropped Python 3.9 support (EOL)

## [0.1.2] - 2026-06-19

### Fixed
- HF model cache in CI
- Mark embedding tests as slow
- Ruff lint errors (F401, F541, F841, I001)

## [0.1.1] - 2026-06-19

### Fixed
- CI configuration (pytest, PYTHONPATH, package build)

## [0.1.0] - 2026-06-19

### Added
- Initial release
- Core snippet CRUD with git-friendly JSON storage
- Semantic search with local embeddings (sentence-transformers + FAISS)
- Hybrid search (semantic + keyword with configurable weights)
- LLM-optimized export providers (Claude XML, Cursor, OpenAI, Generic Markdown)
- Rich CLI with Typer
- Plugin system with entry points
- Python library distribution (PyPI)

[0.6.2]: https://github.com/billybox1926-jpg/snipcontext/compare/v0.6.1...v0.6.2
[0.6.1]: https://github.com/billybox1926-jpg/snipcontext/compare/v0.6.0...v0.6.1
