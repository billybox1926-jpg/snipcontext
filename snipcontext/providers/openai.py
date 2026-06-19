"""OpenAI / ChatGPT-optimized export provider."""

from __future__ import annotations

from snipcontext.core.models import Snippet
from snipcontext.providers.base import BaseProvider, ExportFormat


class OpenAIProvider(BaseProvider):
    """OpenAI ChatGPT-optimized context provider with clear visual separation."""

    name = "openai"
    description = "OpenAI ChatGPT format — clear visual separation"
    format = ExportFormat.PROMPT

    _DIVIDER = "═" * 40

    def export_single(self, snippet: Snippet) -> str:
        lines = [
            self._DIVIDER,
            f"SNIPPET: {snippet.metadata.title or 'Untitled'}",
            self._DIVIDER,
            "",
        ]

        if self.include_metadata:
            if snippet.metadata.description:
                lines.append(f"Description: {snippet.metadata.description}")
            lines.append(f"Language: {snippet.metadata.language.value}")
            if snippet.tags:
                lines.append(f"Tags: {snippet.tag_line}")
            if snippet.metadata.confidence:
                lines.append(f"Confidence: {snippet.metadata.confidence}")
            lines.append("")

        lang = snippet.metadata.language.value
        lines.extend([
            f"```{lang}",
            snippet.content,
            "```",
            "",
        ])
        return "\n".join(lines)

    def export_batch(self, snippets: list[Snippet], title: str = "Code Context") -> str:
        lines = [
            f"{self._DIVIDER}{self._DIVIDER}",
            f"  {title}",
            f"  {len(snippets)} code snippets provided below",
            "  Use these as reference for your response.",
            f"{self._DIVIDER}{self._DIVIDER}",
            "",
        ]
        for snippet in snippets:
            lines.append(self.export_single(snippet))
        return "\n".join(lines)
