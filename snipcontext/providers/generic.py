"""Generic Markdown export provider."""

from __future__ import annotations

from snipcontext.core.models import Snippet
from snipcontext.providers.base import BaseProvider, ExportFormat


class GenericProvider(BaseProvider):
    """Standard Markdown provider for universal LLM compatibility."""

    name = "generic"
    description = "Universal Markdown format — works with any LLM"
    format = ExportFormat.MARKDOWN

    def export_single(self, snippet: Snippet) -> str:
        lines = [f"## {snippet.metadata.title or 'Untitled Snippet'}\n"]

        if self.include_metadata:
            meta = self._metadata_block(snippet)
            if meta:
                lines.append(meta)
                lines.append("")

        lines.append(self._code_block(snippet))
        lines.append("")
        return "\n".join(lines)

    def export_batch(self, snippets: list[Snippet], title: str = "Code Context") -> str:
        lines = [
            f"# {title}",
            "",
            f"> *{len(snippets)} code snippets provided as context*",
            "",
            "---",
            "",
        ]
        for snippet in snippets:
            lines.append(self.export_single(snippet))
        return "\n".join(lines)
