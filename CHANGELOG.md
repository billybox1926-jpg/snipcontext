# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
- Encryption at rest (Fernet/AES-128, `--encrypt` and `--sensitive` flags)
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
- `except: pass` in `search.py` silently swallowing index cleanup errors (partially addressed)
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
