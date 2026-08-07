"""Core import helpers for remote snippet collections."""

from __future__ import annotations

import io
import json
import os
import shutil
import tarfile
import tempfile
from pathlib import Path
from typing import Any

import yaml

from snipcontext.core.models import Language, Snippet, SnippetMetadata

MAX_ARCHIVE_DOWNLOAD_BYTES = 10 * 1024 * 1024
MAX_ARCHIVE_EXTRACTED_BYTES = 10 * 1024 * 1024
MAX_ARCHIVE_MEMBER_COUNT = 500


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


def _is_tar_gz(raw: bytes) -> bool:
    return raw.startswith(b"\x1f\x8b") and b"ustar" in raw[:1024]


def _is_supported_member(member: tarfile.TarInfo) -> bool:
    if member.issym() or member.islnk() or member.isfile() is False:
        return False
    if member.type not in (tarfile.REGTYPE, tarfile.AREGTYPE, tarfile.DIRTYPE):
        return False
    return True


def _safe_member_path(member_name: str, resolved_tmp_dir: str) -> str:
    if os.path.isabs(member_name):
        raise ValueError(f"Absolute paths are not allowed in archives: {member_name}")
    if ".." in member_name.split(os.sep):
        raise ValueError(f"Parent directory traversal is not allowed: {member_name}")

    member_path = os.path.normpath(os.path.join(resolved_tmp_dir, member_name))
    tmp_dir = os.path.normpath(resolved_tmp_dir)

    if not member_path.startswith(tmp_dir + os.sep) and member_path != tmp_dir:
        raise ValueError(f"Member path escapes temp dir: {member_name}")
    return member_path


def import_tar_gz(raw: bytes) -> list[ImportedSnippet]:
    """Import snippets from a `.tar.gz` archive, extracting to a temp directory.

    Extraction uses `tarfile.data_filter` plus manual path-containment and
    symlink/hardlink/special-file rejection.
    """
    if len(raw) > MAX_ARCHIVE_DOWNLOAD_BYTES:
        raise ValueError(f"Archive too large: {len(raw)} bytes > {MAX_ARCHIVE_DOWNLOAD_BYTES}")

    tmp_dir = tempfile.mkdtemp(prefix="snip_import_")
    tmp_dir = os.path.realpath(tmp_dir)
    extracted_bytes = 0
    member_count = 0
    results: list[ImportedSnippet] = []

    try:
        with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as tar:
            members = tar.getmembers()
            if len(members) > MAX_ARCHIVE_MEMBER_COUNT:
                raise ValueError(
                    f"Archive has too many members: {len(members)} > {MAX_ARCHIVE_MEMBER_COUNT}"
                )

            for member in members:
                if not _is_supported_member(member):
                    continue

                try:
                    _safe_member_path(member.name, tmp_dir)
                except ValueError:
                    continue

                member_path = os.path.join(tmp_dir, member.name)
                if member.isdir() or member.type == tarfile.DIRTYPE:
                    os.makedirs(member_path, exist_ok=True)
                    continue

                try:
                    tar.extract(member, tmp_dir, filter=tarfile.data_filter)
                except (tarfile.FilterError, tarfile.OutsideDestinationError, OSError):
                    continue

                try:
                    chunk = Path(member_path).read_bytes()
                except OSError:
                    continue

                extracted_bytes += len(chunk)
                if extracted_bytes > MAX_ARCHIVE_EXTRACTED_BYTES:
                    raise ValueError(
                        f"Decompressed archive too large: {extracted_bytes} bytes > {MAX_ARCHIVE_EXTRACTED_BYTES}"
                    )

                member_count += 1
                if member_count > MAX_ARCHIVE_MEMBER_COUNT:
                    raise ValueError(
                        f"Archive has too many members: {member_count} > {MAX_ARCHIVE_MEMBER_COUNT}"
                    )

                try:
                    text = chunk.decode("utf-8")
                except UnicodeDecodeError:
                    continue

                try:
                    results.extend(parse_import(text))
                except Exception:
                    continue
    finally:
        try:
            shutil.rmtree(tmp_dir, ignore_errors=True)
        except Exception:
            pass

    return results
