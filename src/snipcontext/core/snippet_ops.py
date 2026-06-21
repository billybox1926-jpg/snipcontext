"""Snippet domain business logic.

Pure functions for snippet CRUD operations.
No I/O, no CLI dependencies. All functions accept data as arguments
and return results. The CLI layer handles user interaction.
"""

from __future__ import annotations

from pathlib import Path

from snipcontext.config.settings import Config
from snipcontext.core.models import Language, Snippet, SnippetMetadata
from snipcontext.core.storage import SnippetNotFoundError, StorageEngine

# Extension-to-language mapping for auto-detection
EXT_LANG_MAP: dict[str, str] = {
    "py": "python",
    "js": "javascript",
    "ts": "typescript",
    "jsx": "jsx",
    "tsx": "tsx",
    "html": "html",
    "css": "css",
    "java": "java",
    "go": "go",
    "rs": "rust",
    "cpp": "cpp",
    "c": "c",
    "cs": "csharp",
    "php": "php",
    "rb": "ruby",
    "swift": "swift",
    "sql": "sql",
    "sh": "bash",
    "yml": "yaml",
    "yaml": "yaml",
    "json": "json",
    "toml": "toml",
    "md": "markdown",
    "dockerfile": "dockerfile",
    "tf": "terraform",
}


def resolve_language(language: str, title: str, from_file: bool, content: str) -> str:
    """Resolve the language for a snippet.

    If language is explicitly provided, use it.
    If reading from file, infer from extension.
    Otherwise return empty string (will become Language.UNKNOWN).

    Args:
        language: Explicitly provided language string (may be empty).
        title: Snippet title (used for extension detection if no file).
        from_file: Whether content was read from a file.
        content: The snippet content (used as file path when from_file=True).

    Returns:
        Language string or empty string.
    """
    if language:
        return language
    if from_file:
        ext = Path(content).suffix.lstrip(".").lower()
        return EXT_LANG_MAP.get(ext, "")
    # Try to infer from title extension
    if "." in title:
        ext = title.rsplit(".", 1)[-1].lower()
        return EXT_LANG_MAP.get(ext, "")
    return ""


def auto_title(content: str) -> str:
    """Generate a title from the first line of content.

    Args:
        content: Snippet content.

    Returns:
        First line truncated to 50 chars, or "Untitled Snippet".
    """
    first_line = content.strip().split("\n")[0][:50]
    return first_line or "Untitled Snippet"


def create_snippet(
    content: str,
    title: str,
    description: str,
    language: str,
    tags: list[str],
    encrypt: bool = False,
    encrypted_content: str | None = None,
) -> Snippet:
    """Create a new Snippet model instance.

    Args:
        content: Snippet content (empty string if encrypted).
        title: Snippet title.
        description: Snippet description.
        language: Programming language string.
        tags: List of tags.
        encrypt: Whether the content is encrypted.
        encrypted_content: Encrypted content (if encrypt=True).

    Returns:
        New Snippet instance (not yet persisted).

    Raises:
        ValueError: If content is empty and not encrypted.
    """
    if not content.strip() and not encrypted_content:
        raise ValueError("Content cannot be empty")

    try:
        lang_enum = Language(language) if language else Language.UNKNOWN
    except ValueError:
        lang_enum = Language.UNKNOWN

    if encrypt and encrypted_content:
        return Snippet(
            content="",
            encrypted_content=encrypted_content,
            metadata=SnippetMetadata(
                title=title,
                description=description,
                language=lang_enum,
            ),
            tags=tags,
        )
    return Snippet(
        content=content,
        metadata=SnippetMetadata(
            title=title,
            description=description,
            language=lang_enum,
        ),
        tags=tags,
    )


def add_snippet(
    storage: StorageEngine,
    content: str,
    title: str,
    description: str,
    language: str,
    tags: list[str],
    encrypt: bool = False,
    encrypted_content: str | None = None,
) -> Snippet:
    """Create and persist a new snippet.

    Args:
        storage: Storage engine instance.
        content: Snippet content.
        title: Snippet title.
        description: Snippet description.
        language: Programming language string.
        tags: List of tags.
        encrypt: Whether the content is encrypted.
        encrypted_content: Encrypted content (if encrypt=True).

    Returns:
        The saved Snippet instance.
    """
    snippet = create_snippet(content, title, description, language, tags, encrypt, encrypted_content)
    storage.save(snippet)
    return snippet


def get_snippet(storage: StorageEngine, snippet_id: str) -> Snippet:
    """Retrieve a snippet by ID or prefix.

    Args:
        storage: Storage engine instance.
        snippet_id: Snippet ID or prefix.

    Returns:
        The matching Snippet.

    Raises:
        SnippetNotFoundError: If no matching snippet found.
        ValueError: If multiple snippets match the prefix.
    """
    try:
        return storage.get(snippet_id)
    except SnippetNotFoundError:
        matches = [s for s in storage.iter_all() if s.id.startswith(snippet_id)]
        if len(matches) == 1:
            return matches[0]
        elif len(matches) > 1:
            raise ValueError(f"Multiple matches for prefix '{snippet_id}'")
        raise


def list_snippets(
    storage: StorageEngine,
    tag: str | None = None,
    language: str | None = None,
    sort: str = "updated",
) -> list[Snippet]:
    """List snippets with optional filtering and sorting.

    Args:
        storage: Storage engine instance.
        tag: Filter by tag (optional).
        language: Filter by language (optional).
        sort: Sort field — 'updated', 'created', 'title', 'access'.

    Returns:
        List of matching Snippet instances.
    """
    snippets = storage.list_all()

    if tag:
        tag = tag.strip().lstrip("#").lower()
        snippets = [s for s in snippets if tag in s.tags]
    if language:
        snippets = [s for s in snippets if s.metadata.language.value == language.lower()]

    sort_key = {
        "updated": lambda s: s.updated_at,
        "created": lambda s: s.created_at,
        "title": lambda s: s.metadata.title.lower(),
        "access": lambda s: s.access_count,
    }.get(sort, lambda s: s.updated_at)
    snippets.sort(key=sort_key, reverse=(sort in ("updated", "created", "access")))

    return snippets


def edit_snippet(
    storage: StorageEngine,
    snippet_id: str,
    content: str | None = None,
    title: str | None = None,
    description: str | None = None,
    add_tags: list[str] | None = None,
    remove_tags: list[str] | None = None,
    message: str = "",
) -> Snippet:
    """Edit an existing snippet.

    Args:
        storage: Storage engine instance.
        snippet_id: Snippet ID or prefix.
        content: New content (optional).
        title: New title (optional).
        description: New description (optional).
        add_tags: Tags to add (optional).
        remove_tags: Tags to remove (optional).
        message: Version bump message.

    Returns:
        The updated Snippet instance.

    Raises:
        SnippetNotFoundError: If snippet not found.
    """
    snippet = storage.get(snippet_id)

    snippet.bump_version(message or f"Edit: {title or 'metadata update'}")

    if content:
        snippet.content = content
    if title:
        snippet.metadata.title = title
    if description:
        snippet.metadata.description = description
    if add_tags:
        for t in add_tags:
            snippet.merge_tags([t])
    if remove_tags:
        for t in remove_tags:
            t = t.strip().lstrip("#").lower()
            if t in snippet.tags:
                snippet.tags.remove(t)
                snippet.tags.sort()

    snippet.touch()
    storage.save(snippet)
    return snippet


def delete_snippet(storage: StorageEngine, snippet_id: str) -> Snippet:
    """Delete a snippet.

    Args:
        storage: Storage engine instance.
        snippet_id: Snippet ID or prefix.

    Returns:
        The deleted Snippet instance.

    Raises:
        SnippetNotFoundError: If snippet not found.
    """
    snippet = storage.get(snippet_id)
    storage.delete(snippet.id)
    return snippet


def record_snippet_access(storage: StorageEngine, snippet: Snippet) -> None:
    """Record that a snippet was accessed.

    Args:
        storage: Storage engine instance.
        snippet: The snippet that was accessed.
    """
    snippet.record_access()
    storage.save(snippet)
