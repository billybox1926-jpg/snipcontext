"""Core import helpers for remote snippet collections."""

from __future__ import annotations

import json
from typing import Any

import yaml

from snipcontext.core.models import Language, Snippet, SnippetMetadata


class ImportedSnippet:
    def __init__(self, title: str, content: str, language: str, tags: list[str]) -> None:
        self.title = title
        self.content = content
        self.language = language
        self.tags = tags


def parse_yaml_import(raw: str) -> list[ImportedSnippet]:
    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid YAML import: {exc}") from exc
    if not isinstance(data, list):
        raise ValueError("YAML import must be a list of snippet objects")
    results: list[ImportedSnippet] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or item.get("name") or "Imported Snippet")
        content = str(item.get("content") or item.get("code") or "")
        language = str(item.get("lang") or item.get("language") or "text")
        tags = item.get("tags") or []
        if isinstance(tags, str):
            tags = [tags]
        results.append(
            ImportedSnippet(title=title, content=content, language=language, tags=list(tags))
        )
    return results


def _normalize_tags(tags: Any) -> list[str]:
    if not tags:
        return []
    if isinstance(tags, str):
        return [tags]
    return [str(tag) for tag in tags]


def parse_json_import(raw: str) -> list[ImportedSnippet]:
    data = json.loads(raw)
    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list):
        raise ValueError("JSON import must be an array or a single snippet object")
    results: list[ImportedSnippet] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or item.get("name") or "Imported Snippet")
        content = str(item.get("content") or item.get("code") or "")
        language = str(item.get("lang") or item.get("language") or "text")
        tags = _normalize_tags(item.get("tags"))
        results.append(ImportedSnippet(title=title, content=content, language=language, tags=tags))
    return results


def _parse_frontmatter(raw: str) -> tuple[dict[str, Any], str]:
    """Split a Markdown document into frontmatter dict and body text."""
    if not raw.startswith("---"):
        return {}, raw
    end = raw.find("\n---", 3)
    if end == -1:
        return {}, raw
    frontmatter = yaml.safe_load(raw[3:end]) or {}
    body = raw[end + 4 :].lstrip("\n")
    if not isinstance(frontmatter, dict):
        frontmatter = {}
    return frontmatter, body


def parse_markdown_import(raw: str) -> list[ImportedSnippet]:
    frontmatter, body = _parse_frontmatter(raw)
    title = str(frontmatter.get("title") or frontmatter.get("name") or "Imported Snippet")
    content = str(body or frontmatter.get("content") or frontmatter.get("code") or "")
    language = str(frontmatter.get("lang") or frontmatter.get("language") or "markdown")
    tags = _normalize_tags(frontmatter.get("tags"))
    return [ImportedSnippet(title=title, content=content, language=language, tags=tags)]


def parse_import(raw: str, format: str | None = None) -> list[ImportedSnippet]:
    """Parse an import payload in YAML, JSON, or Markdown-with-frontmatter format.

    When format is None, the parser auto-detects by content shape.
    """
    if format == "json":
        return parse_json_import(raw)
    if format == "markdown":
        return parse_markdown_import(raw)
    if format == "yaml":
        return parse_yaml_import(raw)

    normalized = raw.lstrip()
    if normalized.startswith("{") or normalized.startswith("["):
        try:
            return parse_json_import(raw)
        except (json.JSONDecodeError, ValueError):
            pass
    if normalized.startswith("---"):
        try:
            return parse_markdown_import(raw)
        except Exception:
            pass
    return parse_yaml_import(raw)


def to_snippet(item: ImportedSnippet) -> Snippet:
    """Convert parsed import data into a concrete Snippet instance."""
    try:
        language = Language(item.language)
    except ValueError:
        language = Language.UNKNOWN
    return Snippet(
        content=item.content,
        metadata=SnippetMetadata(
            title=item.title,
            description="",
            language=language,
        ),
        tags=item.tags,
    )
