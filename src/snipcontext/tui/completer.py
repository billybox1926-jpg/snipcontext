"""Auto-completion and fuzzy matching for the REPL."""

from __future__ import annotations

from collections.abc import Iterable

from prompt_toolkit.completion import CompleteEvent, Completer, Completion
from prompt_toolkit.completion.fuzzy_completer import FuzzyCompleter
from prompt_toolkit.document import Document


class SnipContextCompleter(Completer):
    """Context-aware completer for SnipContext commands and values."""

    def __init__(self, registry) -> None:
        self.registry = registry
        self._fuzzy = FuzzyCompleter(self)

    def get_completions(
        self, document: Document, complete_event: CompleteEvent
    ) -> Iterable[Completion]:
        text = document.text
        cursor = document.cursor_position
        if cursor != len(text):
            return
        words = text.split()
        word = words[-1] if words else ""
        if not word.startswith("-") and len(words) == 1 and cursor == len(word):
            yield from self._complete_commands(word)
        else:
            yield from self._complete_values(document, words, word)

    def _complete_commands(self, prefix: str) -> Iterable[Completion]:
        for name, spec in self.registry.commands.items():
            if name.startswith(prefix.lower()):
                yield Completion(name, start_position=-len(prefix))
                for alias in spec.aliases:
                    if alias.startswith(prefix.lower()):
                        yield Completion(alias, start_position=-len(prefix))

    def _complete_values(
        self, document: Document, words: list[str], prefix: str
    ) -> Iterable[Completion]:
        if not words:
            return
        command = words[0].lower()
        if prefix.startswith("-"):
            flags: list[str] = []
            if command in ("list", "ls"):
                flags = ["--tag", "--lang", "--sort"]
            elif command in ("search", "find"):
                flags = ["--mode", "--m", "--limit", "--n", "--threshold", "--t", "--fuzzy", "--f"]
            elif command in ("export", "ex"):
                flags = [
                    "--provider",
                    "--p",
                    "--output",
                    "--o",
                    "--query",
                    "--q",
                    "--id",
                    "--limit",
                    "--n",
                ]
            elif command in ("config", "cfg"):
                flags = ["show", "path", "dirs"]
            elif command == "delete":
                flags = ["--force", "--yes"]
            for flag in flags:
                if flag.startswith(prefix):
                    yield Completion(flag, start_position=-len(prefix))
            return
        if command in ("delete", "get", "edit"):
            try:
                from snipcontext.cli.context import get_context as _get_ctx

                _, storage, _ = _get_ctx()
                for snippet in storage.list_all():
                    if snippet.id.startswith(prefix):
                        yield Completion(snippet.id, start_position=-len(prefix))
                        yield Completion(snippet.id[:6], start_position=-len(prefix))
            except Exception:
                pass
            return
        if command in ("list", "ls") and len(words) >= 2 and words[1].startswith("--"):
            # tag values
            try:
                from snipcontext.cli.context import get_context as _get_ctx

                _, storage, _ = _get_ctx()
                for tag in storage.get_all_tags():
                    if tag.startswith(prefix.lower()):
                        yield Completion(tag, start_position=-len(prefix))
            except Exception:
                pass
