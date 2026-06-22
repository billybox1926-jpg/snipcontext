"""Anthropic Claude-optimized export provider."""

from __future__ import annotations

import html
from typing import TYPE_CHECKING

from snipcontext.providers.base import BaseProvider, ExportFormat

if TYPE_CHECKING:
    from snipcontext.core.models import Snippet


class ClaudeProvider(BaseProvider):
    """Claude-optimized XML context provider.

    Uses Anthropic's recommended XML document structure.
    """

    name = "claude"
    description = "Anthropic Claude XML format — optimal context structure"
    format = ExportFormat.XML

    def export_single(self, snippet: Snippet) -> str:
        lines = [
            f"<source>{snippet.id}</source>",
            f"<title>{html.escape(snippet.metadata.title or 'Untitled')}</title>",
        ]

        if self.include_metadata:
            lines.append("<metadata>")
            if snippet.metadata.description:
                lines.append(
                    f"<description>{html.escape(snippet.metadata.description)}</description>"
                )
            lines.append(f"<language>{snippet.metadata.language.value}</language>")
            if snippet.metadata.framework:
                lines.append(f"<framework>{html.escape(snippet.metadata.framework)}</framework>")
            if snippet.metadata.version:
                lines.append(f"<version>{html.escape(snippet.metadata.version)}</version>")
            if snippet.metadata.source_url:
                lines.append(f"<source_url>{html.escape(snippet.metadata.source_url)}</source_url>")
            if snippet.metadata.author:
                lines.append(f"<author>{html.escape(snippet.metadata.author)}</author>")
            if snippet.tags:
                lines.append(f"<tags>{', '.join(html.escape(t) for t in snippet.tags)}</tags>")
            lines.append(f"<confidence>{html.escape(snippet.metadata.confidence)}</confidence>")
            lines.append(
                f"<llm_optimized>{'true' if snippet.metadata.llm_optimized else 'false'}</llm_optimized>"
            )
            lines.append("</metadata>")

        lang = snippet.metadata.language.value
        escaped_content = html.escape(snippet.content)
        lines.extend(
            [
                "<document_content>",
                f"```{lang}",
                escaped_content,
                "```",
                "</document_content>",
            ]
        )

        return "\n".join(lines)

    def export_batch(self, snippets: list[Snippet], title: str = "Code Context") -> str:
        lines = [
            f"<!-- {title} — {len(snippets)} snippets for Claude -->",
            "<documents>",
        ]
        for i, snippet in enumerate(snippets, 1):
            lines.append(f'<document index="{i}">')
            lines.append(self.export_single(snippet))
            lines.append("</document>")
        lines.append("</documents>")
        return "\n".join(lines)
