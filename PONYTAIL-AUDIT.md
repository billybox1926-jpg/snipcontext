# Ponytail Audit — SnipContext

Date: 2026-06-23
Repo: `billybox1926-jpg/snipcontext`

## Result

Largest cuts come from repeated faiss error handling and legacy facades.
Overall structure (plugin ABCs, multiple index backends) is justified by the plugin/extensibility mission.
No correctness or security issues flagged; scope is over-engineering only.

## Findings (biggest cut first)

`core/search.py` and `core/index_backends.py`: each faiss-using method wraps its own try/except ImportError. Twelve sites in one file, three files total. Extract one `_require_faiss()` helper and call it; delete 10 duplicate blocks.
`plugins/base.py`: `PluginManager` is a legacy static-method facade to `PluginRegistry`. Comments say "legacy"; nothing in the scan shows a second caller. Delete it; point stragglers at `PluginRegistry` directly.
`plugins/registry.py`: `PluginRegistry` singleton. Works, but a module-level instance is enough for this size. `_instance = PluginRegistry()` + `def _registry() -> PluginRegistry: return _instance` drops the class-level `__new__` logic.
`core/storage.py`: five narrow custom exceptions with identical `__init__` signatures. One `StorageError(status, detail, original=None)` carries the same info; delete `SnippetNotFoundError`, `IndexCorruptedError`, `MissingIndexError`, `EncryptionError`.
`core/index_backends.py`: 15 properties for backend metadata. `count`, `is_trained`, `snippet_ids` are already used as properties; the rest (`IndexBackend` abstract property contract) is justified by the multi-backend design. No cut, just noting.

Smallest concrete cut is `cli/snippets.py`: 543 lines, multiple rich console handlers for the same domain. Not broken, but size is a signal.

net: ~-20 lines (legacy facade + exception classes), ~-80 lines (faiss guard duplication), ~-30 lines (singleton templating). ~-130 lines possible.
