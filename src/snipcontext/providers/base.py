"""Base provider interface for LLM-optimized export.

Each provider knows how to format snippets for optimal consumption
by a specific LLM or IDE integration.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import TYPE_CHECKING

from snipcontext.core.sanitization import sanitize_code, sanitize_text

if TYPE_CHECKING:
    from snipcontext.core.models import Snippet


class ExportFormat(str, Enum):
    """Supported export formats."""

    XML = "xml"
    MARKDOWN = "markdown"
    JSON = "json"
    PROMPT = "prompt"


class ProviderError(Exception):
    """Base exception for provider-specific failures."""


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
        raise NotImplementedError

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

    @abstractmethod
    def health_check(self) -> str:
        """Return a simple status string for this provider.

        Implementations should not make network calls by default;
        return ``ok`` when the provider can be instantiated and called.
        """
        raise NotImplementedError

    def _metadata_block(self, snippet: Snippet) -> str:
        """Generate a metadata block for a snippet."""
        meta = snippet.metadata
        lines = []
        if meta.title:
            lines.append(f"**Title:** {sanitize_text(meta.title)}")
        if meta.description:
            lines.append(f"**Description:** {sanitize_text(meta.description)}")
        if meta.language.value != "unknown":
            lines.append(f"**Language:** {meta.language.value}")
        if snippet.tags:
            lines.append(f"**Tags:** {', '.join(sanitize_text(t) for t in snippet.tags)}")
        if meta.framework:
            lines.append(f"**Framework:** {sanitize_text(meta.framework)}")
        if meta.version:
            lines.append(f"**Version:** {sanitize_text(meta.version)}")
        if meta.source_url:
            lines.append(f"**Source:** {sanitize_text(meta.source_url)}")
        if meta.author:
            lines.append(f"**Author:** {sanitize_text(meta.author)}")
        lines.append(f"**Quality:** {meta.confidence}")
        lines.append(f"**LLM-Optimized:** {'Yes' if meta.llm_optimized else 'No'}")
        return "\n".join(lines)

    def _code_block(self, snippet: Snippet) -> str:
        """Wrap code content in appropriate fences.

        For encrypted snippets, returns a placeholder indicating the content is encrypted.
        Content is sanitized to prevent code-fence breakout and terminal escape injection.
        """
        if snippet.encrypted_content:
            return "```\n[ENCRYPTED CONTENT - Use 'sc decrypt <id>' to decrypt]\n```"
        lang = snippet.metadata.language.value
        safe_content = sanitize_code(snippet.content)
        return f"```{lang}\n{safe_content}\n```"
