"""Tests for the import command."""

from __future__ import annotations

import json

import pytest
import yaml
from typer.testing import CliRunner

from snipcontext.cli.app import app
from snipcontext.core.importers import (
    ImportedSnippet,
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
    raw = json.dumps({
        "title": "Single JSON",
        "content": "console.log(1)",
        "lang": "javascript",
        "tags": ["js"],
    })
    results = parse_json_import(raw)
    assert len(results) == 1
    assert results[0].title == "Single JSON"
    assert results[0].language == "javascript"
    assert results[0].tags == ["js"]


def test_parse_json_import_array() -> None:
    raw = json.dumps([
        {"title": "A", "content": "a=1"},
        {"title": "B", "content": "b=2", "tags": ["more"]},
    ])
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
    result = runner.invoke(app, ["import-", str(target)])
    assert result.exit_code == 0, result.output
    assert "Local YAML" in result.output


def test_import_cli_accepts_local_json_file(tmp_path) -> None:
    target = tmp_path / "snippets.json"
    target.write_text(
        json.dumps([{"title": "Local JSON", "content": "console.log(1)", "lang": "javascript"}]),
        encoding="utf-8",
    )
    result = runner.invoke(app, ["import-", str(target)])
    assert result.exit_code == 0, result.output
    assert "Local JSON" in result.output


def test_import_cli_dry_run_json(tmp_path) -> None:
    target = tmp_path / "snippets.json"
    target.write_text(
        json.dumps({"title": "Preview JSON", "content": "x"}),
        encoding="utf-8",
    )
    result = runner.invoke(app, ["import-", str(target), "--dry-run"])
    assert result.exit_code == 0, result.output
    assert "Preview JSON" in result.output
    assert "Dry run enabled" in result.output


def test_import_cli_invalid_format_option(tmp_path) -> None:
    target = tmp_path / "snippets.yaml"
    target.write_text("- title: x\n  content: y\n", encoding="utf-8")
    result = runner.invoke(app, ["import-", str(target), "--format", "xml"])
    assert result.exit_code != 0
    assert "Unsupported format" in result.output


def test_import_cli_missing_file() -> None:
    result = runner.invoke(app, ["import-", "C:/missing/snippets.yaml"])
    assert result.exit_code != 0
    assert "File not found" in result.output


def test_import_cli_rejects_file_scheme() -> None:
    result = runner.invoke(app, ["import-", "file:///C:/tmp/snippets.yaml"])
    assert result.exit_code != 0
    assert "Only https:// URLs are supported" in result.output


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
