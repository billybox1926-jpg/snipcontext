"""Cursor IDE-optimized export provider."""

from __future__ import annotations

from typing import TYPE_CHECKING

from snipcontext.core.sanitization import sanitize_code, sanitize_text
from snipcontext.providers.base import BaseProvider, ExportFormat, ProviderError

if TYPE_CHECKING:
    from snipcontext.core.models import Snippet


class CursorProvider(BaseProvider):
    """Cursor IDE context provider with file-style headers."""

    name = "cursor"
    description = "Cursor IDE format — file-like context headers"
    format = ExportFormat.MARKDOWN

    def export_single(self, snippet: Snippet) -> str:
        lang = snippet.metadata.language.value
        raw_title = snippet.metadata.title or "untitled"
        safe_title = sanitize_text(raw_title).lower()
        safe_title = safe_title.replace(" ", "_").replace("-", "_")[:40]
        pseudo_file = f"{safe_title}.{lang if lang != 'unknown' else 'txt'}"

        lines = [f"[source: {pseudo_file}]"]

        if self.include_metadata:
            meta = snippet.metadata
            if meta.description:
                lines.append(f"// {sanitize_text(meta.description)}")
            if meta.language.value != "unknown":
                lines.append(f"// Language: {meta.language.value}")
            if meta.framework:
                lines.append(f"// Framework: {sanitize_text(meta.framework)}")
            if meta.version:
                lines.append(f"// Version: {sanitize_text(meta.version)}")
            if meta.source_url:
                lines.append(f"// Source: {sanitize_text(meta.source_url)}")
            if snippet.tags:
                lines.append(f"// Tags: {', '.join(sanitize_text(t) for t in snippet.tags)}")

        safe_content = sanitize_code(snippet.content)
        lines.extend(
            [
                f"```{lang}",
                safe_content,
                "```",
                "",
            ]
        )
        return "\n".join(lines)

    def export_batch(self, snippets: list[Snippet], title: str = "Code Context") -> str:
        safe_title = sanitize_text(title)
        lines = [
            f"// {safe_title}",
            f"// {len(snippets)} snippets from SnipContext",
            "",
        ]
        for snippet in snippets:
            lines.append(self.export_single(snippet))
        return "\n".join(lines)

    def health_check(self) -> str:
        return "ok"
