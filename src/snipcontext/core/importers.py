"""Core import helpers for remote snippet collections."""

from __future__ import annotations

import yaml
from pydantic import ValidationError

from snipcontext.core.models import Snippet, SnippetMetadata


class ImportedSnippet:
    def __init__(self, title: str, content: str, language: str, tags: list[str]) -> None:
        self.title = title
        self.content = content
        self.language = language
        self.tags = tags


def parse_yaml_import(raw: str) -> list[ImportedSnippet]:
    data = yaml.safe_load(raw)
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
        results.append(ImportedSnippet(title=title, content=content, language=language, tags=list(tags)))
    return results
