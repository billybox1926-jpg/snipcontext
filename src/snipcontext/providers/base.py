"""Base provider interface for LLM-optimized export.

Each provider knows how to format snippets for optimal consumption
by a specific LLM or IDE integration.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from snipcontext.core.models import Snippet


class ExportFormat(str, Enum):
    """Supported export formats."""

    XML = "xml"
    MARKDOWN = "markdown"
    JSON = "json"
    PROMPT = "prompt"


class BaseProvider(ABC):
    """Abstract base for all LLM export providers.

    Providers transform Snippet collections into strings formatted
    for optimal LLM comprehension and context window usage.
    """

    name: str = ""
    description: str = ""
    format: ExportFormat = ExportFormat.MARKDOWN

    def __init__(self, include_metadata: bool = True) -> None:
        self.include_metadata = include_metadata

    @abstractmethod
    def export_single(self, snippet: Snippet) -> str:
        """Format a single snippet for this provider.

        Returns:
            Formatted string ready for LLM consumption.
        """
        ...

    def export_batch(self, snippets: list[Snippet], title: str = "Code Context") -> str:
        """Format multiple snippets as a unified context block.

        Args:
            snippets: List of snippets to include.
            title: Optional title for the context block.

        Returns:
            Formatted multi-snippet string.
        """
        parts = [f"# {title}\n"]
        for snippet in snippets:
            parts.append(self.export_single(snippet))
            parts.append("---\n")
        return "\n".join(parts)

    def _metadata_block(self, snippet: Snippet) -> str:
        """Generate a metadata block for a snippet."""
        meta = snippet.metadata
        lines = []
        if meta.title:
            lines.append(f"**Title:** {meta.title}")
        if meta.description:
            lines.append(f"**Description:** {meta.description}")
        if meta.language.value != "unknown":
            lines.append(f"**Language:** {meta.language.value}")
        if snippet.tags:
            lines.append(f"**Tags:** {snippet.tag_line}")
        if meta.source_url:
            lines.append(f"**Source:** {meta.source_url}")
        if meta.author:
            lines.append(f"**Author:** {meta.author}")
        lines.append(f"**Quality:** {meta.confidence}")
        lines.append(f"**LLM-Optimized:** {'Yes' if meta.llm_optimized else 'No'}")
        return "\n".join(lines)

    def _code_block(self, snippet: Snippet) -> str:
        """Wrap code content in appropriate fences.

        For encrypted snippets, returns a placeholder indicating the content is encrypted.
        """
        if snippet.encrypted_content:
            return "```\n[ENCRYPTED CONTENT - Use 'sc decrypt <id>' to decrypt]\n```"
        lang = snippet.metadata.language.value
        return f"```{lang}\n{snippet.content}\n```"
