"""Tests for the import command."""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from snipcontext.cli.app import app
from snipcontext.core.importers import parse_yaml_import

runner = CliRunner()


def test_parse_yaml_import_valid():
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


def test_parse_yaml_import_invalid_not_list():
    raw = "title: Bad"
    with pytest.raises(ValueError, match="list of snippet objects"):
        parse_yaml_import(raw)


def test_parse_yaml_import_missing_content():
    raw = """
- title: "No Content"
  lang: python
"""
    results = parse_yaml_import(raw)
    assert len(results) == 1
    assert results[0].content == ""


def test_parse_yaml_import_tags_as_string():
    raw = """
- title: "Single Tag"
  content: "x = 1"
  tags: python
"""
    results = parse_yaml_import(raw)
    assert len(results) == 1
    assert results[0].tags == ["python"]
