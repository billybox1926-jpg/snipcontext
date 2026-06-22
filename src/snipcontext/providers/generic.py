"""Generic Markdown export provider."""

from __future__ import annotations

from typing import TYPE_CHECKING

from snipcontext.core.sanitization import sanitize_text
from snipcontext.providers.base import BaseProvider, ExportFormat

if TYPE_CHECKING:
    from snipcontext.core.models import Snippet


class GenericProvider(BaseProvider):
    """Standard Markdown provider for universal LLM compatibility."""

    name = "generic"
    description = "Universal Markdown format — works with any LLM"
    format = ExportFormat.MARKDOWN

    def export_single(self, snippet: Snippet) -> str:
        safe_title = sanitize_text(snippet.metadata.title or "Untitled Snippet")
        lines = [f"## {safe_title}\n"]

        if self.include_metadata:
            meta = self._metadata_block(snippet)
            if meta:
                lines.append(meta)
                lines.append("")

        lines.append(self._code_block(snippet))
        lines.append("")

        return "\n".join(lines)

    def export_batch(self, snippets: list[Snippet], title: str = "Code Context") -> str:
        safe_title = sanitize_text(title)
        lines = [
            f"# {safe_title}",
            "",
            f"> *{len(snippets)} code snippets provided as context*",
            "",
            "---",
            "",
        ]
        for snippet in snippets:
            lines.append(self.export_single(snippet))
        return "\n".join(lines)

    def health_check(self) -> str:
        return "ok"
