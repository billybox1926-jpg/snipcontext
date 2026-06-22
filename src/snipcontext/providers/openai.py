"""OpenAI / ChatGPT-optimized export provider."""

from __future__ import annotations

from typing import TYPE_CHECKING

from snipcontext.core.sanitization import sanitize_code, sanitize_text
from snipcontext.providers.base import BaseProvider, ExportFormat

if TYPE_CHECKING:
    from snipcontext.core.models import Snippet


class OpenAIProvider(BaseProvider):
    """OpenAI ChatGPT-optimized context provider with clear visual separation."""

    name = "openai"
    description = "OpenAI ChatGPT format — clear visual separation"
    format = ExportFormat.PROMPT

    _DIVIDER = "═" * 40

    def export_single(self, snippet: Snippet) -> str:
        safe_title = sanitize_text(snippet.metadata.title or "Untitled")
        lines = [
            self._DIVIDER,
            f"SNIPPET: {safe_title}",
            self._DIVIDER,
            "",
        ]

        if self.include_metadata:
            if snippet.metadata.description:
                lines.append(f"Description: {sanitize_text(snippet.metadata.description)}")
            lines.append(f"Language: {snippet.metadata.language.value}")
            if snippet.metadata.framework:
                lines.append(f"Framework: {sanitize_text(snippet.metadata.framework)}")
            if snippet.metadata.version:
                lines.append(f"Version: {sanitize_text(snippet.metadata.version)}")
            if snippet.metadata.source_url:
                lines.append(f"Source: {sanitize_text(snippet.metadata.source_url)}")
            if snippet.tags:
                lines.append(f"Tags: {', '.join(sanitize_text(t) for t in snippet.tags)}")
            if snippet.metadata.confidence:
                lines.append(f"Confidence: {snippet.metadata.confidence}")
            lines.append(f"LLM-Optimized: {'Yes' if snippet.metadata.llm_optimized else 'No'}")
            lines.append("")

        lang = snippet.metadata.language.value
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
            f"{self._DIVIDER}{self._DIVIDER}",
            f"  {safe_title}",
            f"  {len(snippets)} code snippets provided below",
            "  Use these as reference for your response.",
            f"{self._DIVIDER}{self._DIVIDER}",
            "",
        ]
        for snippet in snippets:
            lines.append(self.export_single(snippet))
        return "\n".join(lines)
