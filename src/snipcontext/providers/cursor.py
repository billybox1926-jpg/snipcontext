"""Cursor IDE-optimized export provider."""

from __future__ import annotations

from typing import TYPE_CHECKING

from snipcontext.providers.base import BaseProvider, ExportFormat

if TYPE_CHECKING:
    from snipcontext.core.models import Snippet


class CursorProvider(BaseProvider):
    """Cursor IDE context provider with file-style headers."""

    name = "cursor"
    description = "Cursor IDE format — file-like context headers"
    format = ExportFormat.MARKDOWN

    def export_single(self, snippet: Snippet) -> str:
        lang = snippet.metadata.language.value
        safe_title = (snippet.metadata.title or "untitled").lower()
        safe_title = safe_title.replace(" ", "_").replace("-", "_")[:40]
        pseudo_file = f"{safe_title}.{lang if lang != 'unknown' else 'txt'}"

        lines = [f"[source: {pseudo_file}]"]

        if self.include_metadata and snippet.metadata.description:
            lines.append(f"// {snippet.metadata.description}")

        lines.extend([
            f"```{lang}",
            snippet.content,
            "```",
            "",
        ])
        return "\n".join(lines)

    def export_batch(self, snippets: list[Snippet], title: str = "Code Context") -> str:
        lines = [
            f"// {title}",
            f"// {len(snippets)} snippets from SnipContext",
            "",
        ]
        for snippet in snippets:
            lines.append(self.export_single(snippet))
        return "\n".join(lines)
