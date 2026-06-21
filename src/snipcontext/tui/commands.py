"""REPL command registry and handlers.

Maps user input to core business logic functions. Each handler accepts
positional args and keyword arguments parsed from the input line and
returns a plain Python result that the TUI formatter can render.
"""

from __future__ import annotations

import shlex
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from snipcontext.core.config_ops import get_config_paths, get_config_values
from snipcontext.core.crypto_ops import decrypt_content, encrypt_content
from snipcontext.core.search_ops import ensure_index, search_snippets
from snipcontext.core.snippet_ops import (
    create_snippet,
    delete_snippet,
    edit_snippet,
    get_snippet,
    list_snippets,
    record_snippet_access,
)
from snipcontext.plugins.base import PluginManager


@dataclass
class CommandSpec:
    """Declarative description of a REPL command."""

    name: str
    description: str
    aliases: Sequence[str] = ()
    handler: Callable[..., Any] | None = None


class CommandRegistry:
    """Registry that stores commands and dispatches parsed input."""

    def __init__(self) -> None:
        self.commands: dict[str, CommandSpec] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        self.register(CommandSpec("add", "Add a snippet", aliases=["a"], handler=self._add))
        self.register(CommandSpec("get", "Get a snippet", aliases=["show"], handler=self._get))
        self.register(CommandSpec("list", "List snippets", aliases=["ls"], handler=self._list))
        self.register(CommandSpec("edit", "Edit a snippet", aliases=["update"], handler=self._edit))
        self.register(
            CommandSpec("delete", "Delete a snippet", aliases=["rm"], handler=self._delete)
        )
        self.register(
            CommandSpec("search", "Search snippets", aliases=["find"], handler=self._search)
        )
        self.register(
            CommandSpec("export", "Export snippets", aliases=["ex"], handler=self._export)
        )
        self.register(
            CommandSpec("config", "Config subcommands", aliases=["cfg"], handler=self._config)
        )
        self.register(CommandSpec("stats", "Show stats", aliases=["stat"], handler=self._stats))
        self.register(CommandSpec("encrypt", "Encrypt a snippet", handler=self._encrypt))
        self.register(CommandSpec("decrypt", "Decrypt a snippet", handler=self._decrypt))
        self.register(CommandSpec("watch", "Watch snippets dir", handler=self._watch))
        self.register(CommandSpec("index", "Index all snippets", handler=self._index))
        self.register(
            CommandSpec(
                "build-index", "Build search index", aliases=["build"], handler=self._build_index
            )
        )
        self.register(CommandSpec("providers", "List providers", handler=self._providers))

    def register(self, spec: CommandSpec) -> None:
        self.commands[spec.name] = spec
        for alias in spec.aliases:
            self.commands[alias] = spec

    def execute(self, user_input: str) -> Any:
        if not user_input or not user_input.strip():
            return None
        tokens = shlex.split(user_input)
        name = tokens[0].lower()
        spec = self.commands.get(name)
        if spec is None or spec.handler is None:
            return {"type": "error", "message": f"Unknown command: {name}"}
        args, kwargs = _parse_args(tokens[1:])
        try:
            return spec.handler(args, kwargs)
        except SystemExit:
            raise
        except Exception as exc:
            return {"type": "error", "message": str(exc)}

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get_context(self):
        from snipcontext.cli.context import get_context as _get_context_fn

        return _get_context_fn()

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------

    def _add(self, args: list[str], kwargs: dict[str, Any]) -> Any:
        config, storage, search = self._get_context()
        content = args[0] if args else ""
        if kwargs.get("file") or kwargs.get("from_file"):
            path = Path(content)
            if not path.exists():
                raise FileNotFoundError(f"File not found: {content}")
            content = path.read_text()
            title = kwargs.get("title", "") or path.stem
            language = (
                kwargs.get("language", "")
                or kwargs.get("lang", "")
                or _EXT_LANG_MAP.get(path.suffix.lstrip(".").lower(), "")
            )
        else:
            title = kwargs.get("title", "") or kwargs.get("t", "")
            language = kwargs.get("language", "") or kwargs.get("lang", "")

        if not title:
            title = content.strip().split("\n")[0][:50] or "Untitled Snippet"
        if not content.strip():
            raise ValueError("Content cannot be empty")
        tags = _coerce_tags(kwargs.get("tags", []))
        encrypt = bool(kwargs.get("encrypt") or kwargs.get("encrypted"))
        if encrypt and not config.encryption.enabled:
            raise RuntimeError("Encryption is not enabled")
        snippet = create_snippet(
            content=content,
            title=title,
            description=kwargs.get("description", "") or kwargs.get("desc", ""),
            language=language,
            tags=tags,
            encrypt=encrypt,
        )
        storage.save(snippet)
        return {"type": "snippet", "item": snippet}

    def _get(self, args: list[str], kwargs: dict[str, Any]) -> Any:
        if not args:
            raise ValueError("Snippet ID required")
        _, storage, _ = self._get_context()
        snippet_id = args[0]
        try:
            snippet = get_snippet(storage, snippet_id)
        except Exception:
            snippet = storage.get(snippet_id)
        record_snippet_access(storage, snippet)
        storage.save(snippet)
        return {"type": "snippet", "item": snippet}

    def _list(self, args: list[str], kwargs: dict[str, Any]) -> Any:
        _, storage, _ = self._get_context()
        tag = kwargs.get("tag") or kwargs.get("tags") or kwargs.get("t")
        language = kwargs.get("language") or kwargs.get("lang") or kwargs.get("l")
        sort = kwargs.get("sort") or kwargs.get("s") or "updated"
        snippets = list_snippets(storage, tag=tag, language=language, sort=sort)
        if not snippets:
            return {"type": "message", "message": "No snippets found."}
        return {"type": "snippet_list", "items": snippets}

    def _edit(self, args: list[str], kwargs: dict[str, Any]) -> Any:
        if not args:
            raise ValueError("Snippet ID required")
        _, storage, _ = self._get_context()
        snippet_id = args[0]
        snippet = edit_snippet(
            storage,
            snippet_id,
            content=kwargs.get("content") or kwargs.get("c"),
            title=kwargs.get("title") or kwargs.get("t"),
            description=kwargs.get("description") or kwargs.get("desc") or kwargs.get("d"),
            add_tags=_coerce_tags(kwargs.get("add_tag", [])),
            remove_tags=_coerce_tags(kwargs.get("remove_tag", [])),
            message=kwargs.get("message", "") or kwargs.get("m", ""),
        )
        return {"type": "snippet", "item": snippet}

    def _delete(self, args: list[str], kwargs: dict[str, Any]) -> Any:
        if not args:
            raise ValueError("Snippet ID required")
        _, storage, _ = self._get_context()
        snippet_id = args[0]
        snippet = delete_snippet(storage, snippet_id)
        return {"type": "snippet", "item": snippet}

    def _search(self, args: list[str], kwargs: dict[str, Any]) -> Any:
        if not args:
            raise ValueError("Search query required")
        query = args[0]
        _, storage, search = self._get_context()
        ensure_index(storage, search)
        results = search_snippets(
            storage,
            search,
            query,
            mode=kwargs.get("mode") or kwargs.get("m", "hybrid"),
            top_k=int(kwargs.get("top_k") or kwargs.get("n") or kwargs.get("limit") or 10),
            threshold=kwargs.get("threshold") or kwargs.get("t"),
            fuzzy=bool(kwargs.get("fuzzy") or kwargs.get("f")),
        )
        if not results:
            return {"type": "message", "message": f"No results for '{query}'"}
        return {"type": "search_results", "items": results}

    def _export(self, args: list[str], kwargs: dict[str, Any]) -> Any:
        config, storage, search = self._get_context()
        provider = kwargs.get("provider") or kwargs.get("p") or "generic"
        output = kwargs.get("output") or kwargs.get("o")
        top_k = int(kwargs.get("top_k") or kwargs.get("n") or kwargs.get("limit") or 10)
        snippets: list[Any] = []
        if kwargs.get("id") or kwargs.get("ids"):
            raw_ids = kwargs.get("id") or kwargs.get("ids")
            ids = (
                _coerce_tags(raw_ids)
                if not isinstance(raw_ids, list)
                else [str(x) for x in raw_ids]
            )
            for sid in ids:
                try:
                    snippets.append(storage.get(sid))
                except Exception:
                    pass
        elif kwargs.get("query") or kwargs.get("q") or args:
            query = kwargs.get("query") or kwargs.get("q") or args[0]
            ensure_index(storage, search)
            results = search_snippets(storage, search, query, top_k=top_k)
            snippets = [r.snippet for r in results]
        else:
            snippets = storage.list_all()
        if not snippets:
            return {"type": "message", "message": "No snippets to export."}
        pm = PluginManager()
        pm.load_builtin_providers()
        prov = pm.get_provider(provider)
        formatted = prov.export_batch(snippets)
        if output:
            Path(output).write_text(formatted)
            return {"type": "message", "message": f"Exported {len(snippets)} snippets to {output}"}
        return {"type": "export", "output": formatted}

    def _config(self, args: list[str], kwargs: dict[str, Any]) -> Any:
        config, _, _ = self._get_context()
        sub = (args[0] if args else "show").lower()
        if sub in ("show", "get"):
            values = get_config_values(config)
            return {"type": "config", "data": values}
        if sub in ("path", "dirs"):
            paths = get_config_paths(config)
            return {"type": "config_paths", "data": paths}
        return {"type": "error", "message": f"Unknown config subcommand: {sub}"}

    def _stats(self, args: list[str], kwargs: dict[str, Any]) -> Any:
        _, storage, _ = self._get_context()
        data = storage.get_stats()
        if data.get("total_snippets", 0) == 0:
            return {"type": "message", "message": "No snippets in your collection yet."}
        return {"type": "stats", "data": data}

    def _encrypt(self, args: list[str], kwargs: dict[str, Any]) -> Any:
        if not args:
            raise ValueError("Snippet ID required")
        config, storage, _ = self._get_context()
        snippet_id = args[0]
        snippet = storage.get(snippet_id)
        encrypted = encrypt_content(config, storage, snippet.content)
        snippet.encrypted_content = encrypted
        snippet.content = ""
        storage.save(snippet)
        return {"type": "message", "message": f"Encrypted snippet: {snippet.metadata.title}"}

    def _decrypt(self, args: list[str], kwargs: dict[str, Any]) -> Any:
        if not args:
            raise ValueError("Snippet ID required")
        config, storage, _ = self._get_context()
        snippet_id = args[0]
        snippet = storage.get(snippet_id)
        decrypted = decrypt_content(config, storage, snippet.encrypted_content)
        snippet.content = decrypted
        snippet.encrypted_content = None
        storage.save(snippet)
        return {"type": "message", "message": f"Decrypted snippet: {snippet.metadata.title}"}

    def _watch(self, args: list[str], kwargs: dict[str, Any]) -> Any:
        config, storage, search = self._get_context()
        from snipcontext.core.watch_ops import create_watcher, is_watcher_enabled

        if not is_watcher_enabled(config):
            return {"type": "message", "message": "Watcher is disabled in config."}
        watcher = create_watcher(config, search, storage)
        watcher.start()
        return {"type": "message", "message": "Watcher started."}

    def _index(self, args: list[str], kwargs: dict[str, Any]) -> Any:
        config, storage, search = self._get_context()
        snippets = storage.list_all()
        if not snippets:
            return {"type": "message", "message": "No snippets to index."}
        search.index_snippets(snippets)
        return {"type": "message", "message": f"Index complete. {len(snippets)} snippets indexed."}

    def _build_index(self, args: list[str], kwargs: dict[str, Any]) -> Any:
        force = bool(kwargs.get("force") or kwargs.get("f"))
        config, storage, search = self._get_context()
        if not force and search.indices_ready:
            return {"type": "message", "message": "Index already exists."}
        snippets = storage.list_all()
        if not snippets:
            return {"type": "message", "message": "No snippets to index."}
        search.index_snippets(snippets)
        return {"type": "message", "message": f"Index complete. {len(snippets)} snippets indexed."}

    def _providers(self, args: list[str], kwargs: dict[str, Any]) -> Any:
        pm = PluginManager()
        pm.load_builtin_providers()
        providers: list[tuple[str, str, str]] = []
        for name in pm.list_providers():
            try:
                p = pm._providers.get(name)
                desc = pm.list_providers().get(name, "")
                fmt = getattr(p, "format", "?")
            except Exception:
                desc = ""
                fmt = "?"
            providers.append((name, desc, str(fmt)))
        return {"type": "providers", "items": providers}


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

_EXT_LANG_MAP: dict[str, str] = {
    "py": "python",
    "js": "javascript",
    "ts": "typescript",
    "jsx": "jsx",
    "tsx": "tsx",
    "html": "html",
    "css": "css",
    "java": "java",
    "go": "go",
    "rs": "rust",
    "cpp": "cpp",
    "c": "c",
    "cs": "csharp",
    "php": "php",
    "rb": "ruby",
    "swift": "swift",
    "sql": "sql",
    "sh": "bash",
    "yml": "yaml",
    "yaml": "yaml",
    "json": "json",
    "toml": "toml",
    "md": "markdown",
    "dockerfile": "dockerfile",
    "tf": "terraform",
}


def _coerce_tags(value: Any) -> list[str]:
    if isinstance(value, list):
        tags: list[str] = []
        for item in value:
            tags.extend(str(item).replace(",", " ").split())
        return sorted({t.strip().lower() for t in tags if t.strip()})
    if isinstance(value, str):
        return sorted({t.strip().lower() for t in value.replace(",", " ").split() if t.strip()})
    return []


def _parse_args(tokens: list[str]) -> tuple[list[str], dict[str, Any]]:
    positional: list[str] = []
    kwargs: dict[str, Any] = {}
    it = iter(tokens)
    for token in it:
        if token.startswith("-"):
            key = token.lstrip("-").replace("-", "_")
            value: Any
            if "=" in token:
                k, v = token.split("=", 1)
                key = k.lstrip("-").replace("-", "_")
                value = v
            else:
                nxt = next(it, None)
                if nxt is None or nxt.startswith("-"):
                    value = True
                else:
                    value = nxt
            kwargs[key] = value
        else:
            positional.append(token)
    return positional, kwargs
