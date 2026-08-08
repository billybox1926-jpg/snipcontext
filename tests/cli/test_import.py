"""Tests for the import command."""

from __future__ import annotations

import io
import json
import tarfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml
from typer.testing import CliRunner

import snipcontext.core.importers as importers
from snipcontext.cli.app import app
from snipcontext.core.importers import (
    MAX_ARCHIVE_DOWNLOAD_BYTES,
    ImportedSnippet,
    _is_supported_member,
    _is_tar_gz,
    _safe_member_path,
    import_tar_gz,
    parse_import,
    parse_json_import,
    parse_markdown_import,
    parse_yaml_import,
    to_snippet,
)

runner = CliRunner()


def test_parse_yaml_import_valid() -> None:
    raw = """
- title: "HTTP Client"
  content: "import requests"
  lang: python
  tags: [http, requests]
- title: "JSON Load"
  content: "import json"
  lang: python
  tags: [json]
"""
    results = parse_yaml_import(raw)
    assert len(results) == 2
    assert results[0].title == "HTTP Client"
    assert results[0].language == "python"
    assert results[0].tags == ["http", "requests"]
    assert results[1].title == "JSON Load"
    assert results[1].content == "import json"


def test_parse_yaml_import_invalid_not_list() -> None:
    raw = "title: Bad"
    with pytest.raises(ValueError, match="list of snippet objects"):
        parse_yaml_import(raw)


def test_parse_yaml_import_missing_content() -> None:
    raw = """
- title: "No Content"
  lang: python
"""
    results = parse_yaml_import(raw)
    assert len(results) == 1
    assert results[0].content == ""


def test_parse_yaml_import_tags_as_string() -> None:
    raw = """
- title: "Single Tag"
  content: "x = 1"
  tags: python
"""
    results = parse_yaml_import(raw)
    assert len(results) == 1
    assert results[0].tags == ["python"]


def test_parse_yaml_import_rejects_unsafe_payload() -> None:
    raw = """
- title: "Evil"
  content: "x"
  tags: [t]
"""
    # Trailing scalar after list is ignored by safe_load; the real risk is
    # object construction tags, which safe_load must refuse.
    risky = raw + '!!python/object/apply:os.system ["echo pwned"]'
    with pytest.raises(ValueError):
        parse_yaml_import(risky)


def test_parse_json_import_object() -> None:
    raw = json.dumps(
        {
            "title": "Single JSON",
            "content": "console.log(1)",
            "lang": "javascript",
            "tags": ["js"],
        }
    )
    results = parse_json_import(raw)
    assert len(results) == 1
    assert results[0].title == "Single JSON"
    assert results[0].language == "javascript"
    assert results[0].tags == ["js"]


def test_parse_json_import_array() -> None:
    raw = json.dumps(
        [
            {"title": "A", "content": "a=1"},
            {"title": "B", "content": "b=2", "tags": ["more"]},
        ]
    )
    results = parse_json_import(raw)
    assert [item.title for item in results] == ["A", "B"]
    assert results[1].tags == ["more"]


def test_parse_json_import_invalid() -> None:
    with pytest.raises((ValueError, TypeError)):
        parse_json_import("not-json")


def test_parse_markdown_import_frontmatter() -> None:
    raw = "---\ntitle: Markdown Snippet\nlang: python\ntags:\n  - markdown\n---\nprint('hello')\n"
    results = parse_markdown_import(raw)
    assert len(results) == 1
    assert results[0].title == "Markdown Snippet"
    assert "print('hello')" in results[0].content
    assert results[0].tags == ["markdown"]


def test_parse_markdown_import_missing_frontmatter() -> None:
    raw = "Just a body.\n"
    results = parse_markdown_import(raw)
    assert len(results) == 1
    assert results[0].title == "Imported Snippet"
    assert results[0].content == "Just a body.\n"


def test_parse_markdown_import_rejects_unsafe_frontmatter() -> None:
    raw = "---\ntitle: Evil\nlang: python\n!!python/object/apply:os.system ['echo pwned']\n---\nbody\n"
    with pytest.raises((ValueError, yaml.YAMLError)):
        parse_markdown_import(raw)


def test_parse_import_auto_detects_json() -> None:
    raw = json.dumps({"title": "Auto JSON", "content": "x=1"})
    results = parse_import(raw)
    assert len(results) == 1
    assert results[0].title == "Auto JSON"


def test_parse_import_auto_detects_markdown_frontmatter() -> None:
    raw = "---\ntitle: Auto MD\n---\nbody\n"
    results = parse_import(raw)
    assert len(results) == 1
    assert results[0].title == "Auto MD"


def test_parse_import_explicit_format_overrides_auto_detect() -> None:
    raw = '{"title": "x", "content": "y"}'
    with pytest.raises(ValueError, match="list of snippet objects"):
        parse_import(raw, format="yaml")


def test_import_cli_accepts_local_yaml_file(tmp_path) -> None:
    target = tmp_path / "snippets.yaml"
    target.write_text(
        """
- title: "Local YAML"
  content: "print(1)"
  lang: python
  tags: [local]
""",
        encoding="utf-8",
    )
    result = runner.invoke(app, ["import", str(target)])
    assert result.exit_code == 0, result.output
    assert "Local YAML" in result.output


def test_import_cli_accepts_local_json_file(tmp_path) -> None:
    target = tmp_path / "snippets.json"
    target.write_text(
        json.dumps([{"title": "Local JSON", "content": "console.log(1)", "lang": "javascript"}]),
        encoding="utf-8",
    )
    result = runner.invoke(app, ["import", str(target)])
    assert result.exit_code == 0, result.output
    assert "Local JSON" in result.output


def test_import_cli_dry_run_json(tmp_path) -> None:
    target = tmp_path / "snippets.json"
    target.write_text(
        json.dumps({"title": "Preview JSON", "content": "x"}),
        encoding="utf-8",
    )
    result = runner.invoke(app, ["import", str(target), "--dry-run"])
    assert result.exit_code == 0, result.output
    assert "Preview JSON" in result.output
    assert "Dry run/preview enabled" in result.output


def test_import_cli_invalid_format_option(tmp_path) -> None:
    target = tmp_path / "snippets.yaml"
    target.write_text("- title: x\n  content: y\n", encoding="utf-8")
    result = runner.invoke(app, ["import", str(target), "--format", "xml"])
    assert result.exit_code != 0
    assert "Unsupported format" in result.output


def test_import_cli_missing_file() -> None:
    result = runner.invoke(app, ["import", "C:/missing/snippets.yaml"])
    assert result.exit_code != 0
    assert "File not found" in result.output


def test_import_cli_rejects_file_scheme() -> None:
    result = runner.invoke(app, ["import", "file:///C:/tmp/snippets.yaml"])
    assert result.exit_code != 0
    assert "Only https:// URLs or built-in collections are supported" in result.output


def test_parse_import_yaml_preferred_over_json_like_fragment() -> None:
    raw = "- title: x\n  content: y\n"
    results = parse_import(raw)
    assert len(results) == 1
    assert results[0].title == "x"


def test_parse_import_json_in_yaml_style_file_auto_detects_json() -> None:
    raw = '[{"title": "Array JSON", "content": "a=1"}]'
    results = parse_import(raw)
    assert len(results) == 1
    assert results[0].title == "Array JSON"


def test_to_snippet_builds_real_domain_snippet() -> None:
    item = ImportedSnippet(title="T", content="c", language="python", tags=["a"])
    snippet = to_snippet(item)
    assert snippet.metadata.title == "T"
    assert snippet.content == "c"
    assert snippet.metadata.language.value == "python"
    assert snippet.tags == ["a"]


def test_is_tar_gz_detects_gzip_magic() -> None:
    assert _is_tar_gz(b"\x1f\x8b\x08\x00ustar\x00\x00") is True
    assert _is_tar_gz(b"not-a-tar") is False


def test_safe_member_path_blocks_traversal() -> None:
    with pytest.raises(ValueError, match="Parent directory traversal is not allowed"):
        _safe_member_path("../../etc/passwd", "/tmp/snip_import_abc")
    with pytest.raises(ValueError, match="Parent directory traversal is not allowed"):
        _safe_member_path(r"..\..\etc\passwd", "/tmp/snip_import_abc")


def test_safe_member_path_blocks_absolute() -> None:
    with pytest.raises(ValueError, match="Absolute paths"):
        _safe_member_path("C:/etc/passwd", "/tmp/snip_import_abc")


def test_safe_member_path_allows_relative() -> None:
    resolved = _safe_member_path("snippets/a.yaml", "/tmp/snip_import_abc")
    assert resolved.replace("\\", "/").startswith("/tmp/snip_import_abc/")


def test_is_supported_member_rejects_symlink() -> None:
    member = tarfile.TarInfo(name="link.py")
    member.type = tarfile.SYMTYPE
    member.linkname = "target.py"
    assert _is_supported_member(member) is False


def test_import_tar_gz_happy_path(tmp_path: Path) -> None:
    archive = tmp_path / "snippets.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        info = tarfile.TarInfo(name="snippet.yaml")
        payload = b'- title: Archive YAML\n  content: "x=1"\n  lang: python\n'
        info.size = len(payload)
        tar.addfile(info, io.BytesIO(payload))
    snippets = import_tar_gz(archive.read_bytes())
    assert len(snippets) == 1
    assert snippets[0].title == "Archive YAML"


def test_import_tar_gz_rejects_traversal_member(tmp_path: Path) -> None:
    archive = tmp_path / "evil.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        info = tarfile.TarInfo(name="../../etc/cron.d/evil")
        payload = b"- title: Evil\n  content: x\n"
        info.size = len(payload)
        tar.addfile(info, io.BytesIO(payload))
    snippets = import_tar_gz(archive.read_bytes())
    assert snippets == []


def test_import_tar_gz_rejects_symlink_member(tmp_path: Path) -> None:
    archive = tmp_path / "symlink.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        info = tarfile.TarInfo(name="link.py")
        info.type = tarfile.SYMTYPE
        info.linkname = "/etc/passwd"
        tar.addfile(info)
    snippets = import_tar_gz(archive.read_bytes())
    assert snippets == []


def test_import_tar_gz_rejects_oversized_payload() -> None:
    payload = b"\x1f\x8b\x08\x00" + b"\x00" * (MAX_ARCHIVE_DOWNLOAD_BYTES + 1)
    with pytest.raises(ValueError, match="Archive too large"):
        import_tar_gz(payload)


def test_import_tar_gz_cleans_up_temp_dir(tmp_path: Path) -> None:
    archive = tmp_path / "clean.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        info = tarfile.TarInfo(name="snippet.yaml")
        payload = b"- title: Clean\n  content: ok\n"
        info.size = len(payload)
        tar.addfile(info, io.BytesIO(payload))
    import_tar_gz(archive.read_bytes())
    temp_dirs = [p for p in tmp_path.glob("snip_import_*") if p.is_dir()]
    assert temp_dirs == []


def test_import_cli_accepts_local_tar_gz_file(tmp_path: Path) -> None:
    target = tmp_path / "snippets.tar.gz"
    with tarfile.open(target, "w:gz") as tar:
        info = tarfile.TarInfo(name="snippet.yaml")
        payload = b"- title: Tar YAML\n  content: hi\n"
        info.size = len(payload)
        tar.addfile(info, io.BytesIO(payload))
    result = runner.invoke(app, ["import", str(target), "--format", "tar.gz"])
    assert result.exit_code == 0, result.output


def test_import_cli_builtin_collection_preview() -> None:
    result = runner.invoke(app, ["import", "snipcontext:python-stdlib", "--list"])
    assert result.exit_code == 0, result.output
    assert "JSON Load" in result.output
    assert "Pathlib Read File" in result.output


def test_import_cli_builtin_collection_import(tmp_path: Path) -> None:
    # Use a temp project-local directory so storage and index are isolated.
    from snipcontext.config.settings import Config, StorageConfig
    from snipcontext.core.storage import StorageEngine
    from snipcontext.cli.context import reset_context

    storage_root = tmp_path / "collection"
    config = Config(
        storage=StorageConfig(
            data_dir=storage_root,
            snippets_dir="snippets",
            index_dir="index",
        )
    )
    reset_context()
    from snipcontext.config.settings import get_config

    # Monkey-patch get_config to return the temp config for the CLI run.
    original_get_config = get_config
    try:
        import snipcontext.config.settings as settings_module

        settings_module.get_config = lambda: config  # type: ignore[assignment]
        reset_context()
        storage = StorageEngine(config)
        result = runner.invoke(app, ["import", "snipcontext:python-stdlib"])
        assert result.exit_code == 0, result.output
        assert "Imported: JSON Load" in result.output
        assert "Imported: Temporary File" in result.output
        assert storage.count() == 4
    finally:
        settings_module.get_config = original_get_config  # type: ignore[assignment]


def test_import_cli_refreshes_search_index(tmp_path: Path) -> None:
    import yaml
    from snipcontext.cli.import_ import _get_context

    target = tmp_path / "snippets.yaml"
    target.write_text(
        """
- title: "Search Refresh"
  content: "print(1)"
  lang: python
  tags: [test]
""",
        encoding="utf-8",
    )

    from snipcontext.core.models import Snippet, SnippetMetadata, Language

    snippet = Snippet(
        content="print(1)",
        metadata=SnippetMetadata(title="Search Refresh", description="", language=Language.PYTHON),
        tags=["test"],
    )

    mock_config = MagicMock()
    storage = MagicMock()
    storage.find_by_content_hash.return_value = None
    storage.save.return_value = None
    storage.list_all.return_value = [snippet]

    search = MagicMock()
    search.indices_ready = True
    search.add_snippet = MagicMock()
    search.rebuild_keyword_index = MagicMock()
    search.index_snippets = MagicMock()

    with patch("snipcontext.cli.import_._get_context", return_value=(mock_config, storage, search)):
        result = runner.invoke(app, ["import", str(target)])

    assert result.exit_code == 0, result.output
    search.add_snippet.assert_called_once()
    search.rebuild_keyword_index.assert_called_once_with([snippet])


def test_import_tar_gz_layered_defense_rejects_traversal_even_without_data_filter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import warnings

    monkeypatch.delattr(tarfile, "data_filter", raising=False)
    monkeypatch.setattr(importers, "tarfile", tarfile, raising=False)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        archive = _build_tar_gz([("../../etc/cron.d/evil", b"- title: Evil\n  content: x\n")])
    snippets = import_tar_gz(archive)
    assert snippets == []


def test_import_tar_gz_incremental_cap_triggers_during_extraction(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(importers, "MAX_ARCHIVE_EXTRACTED_BYTES", 512)
    archive = tmp_path / "bomb.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        info = tarfile.TarInfo(name="member.txt")
        payload = b"x" * 2048
        info.size = len(payload)
        tar.addfile(info, io.BytesIO(payload))
    with pytest.raises(ValueError, match="Decompressed archive too large"):
        import_tar_gz(archive.read_bytes())


def _build_tar_gz(
    members: list[tuple[str, bytes]], compressed_size_cap: int | None = None
) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for name, payload in members:
            info = tarfile.TarInfo(name=name)
            info.size = len(payload)
            tar.addfile(info, io.BytesIO(payload))
    data = buf.getvalue()
    if compressed_size_cap is not None and len(data) < compressed_size_cap:
        data += b"\x00" * (compressed_size_cap - len(data))
    return data
