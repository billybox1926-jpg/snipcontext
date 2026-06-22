"""End-to-end CLI contract tests for user-facing flows."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from snipcontext.cli.app import app
from snipcontext.plugins.base import PluginManifest
from snipcontext.plugins.registry import PluginRegistry
from snipcontext.providers.base import BaseProvider, ExportFormat

runner = CliRunner()


def _env(temp_dir: Path) -> dict[str, str]:
    return {
        "SNIPCONTEXT_STORAGE__DATA_DIR": str(temp_dir),
        "SNIPCONTEXT_STORAGE__SNIPPETS_DIR": "snippets",
        "SNIPCONTEXT_STORAGE__INDEX_DIR": "index",
    }


def _invoke(temp_dir: Path, args: list[str], **kwargs: Any):
    return runner.invoke(app, args, env=_env(temp_dir), **kwargs)


def _snippet_id(output: str) -> str:
    match = re.search(r"ID:\s*([A-Za-z0-9_-]+)", output)
    assert match is not None, output
    return match.group(1)


@pytest.fixture(autouse=True)
def _reset_registry() -> None:
    PluginRegistry._instance = None
    yield
    PluginRegistry._instance = None


class FakeE2EProvider(BaseProvider):
    """Entry-point provider used to prove CLI discovery is end-to-end."""

    manifest = PluginManifest(
        name="e2e-provider",
        version="9.9.9",
        api_version="0.3.0",
        description="E2E fake provider",
    )
    name = "e2e-provider"
    description = "E2E fake provider"
    format = ExportFormat.MARKDOWN

    def export_single(self, snippet):  # type: ignore[no-untyped-def]
        return f"E2E::{snippet.metadata.title}::{snippet.content}"

    def health_check(self) -> str:
        return "ok"


def test_add_list_get_roundtrip(temp_dir: Path, mock_embeddings: Any) -> None:
    add = _invoke(
        temp_dir,
        [
            "add",
            "print('phase 5')",
            "--title",
            "Phase5",
            "--lang",
            "python",
            "--tag",
            "e2e",
        ],
    )
    assert add.exit_code == 0, add.output
    assert "Added snippet" in add.output
    assert "Phase5" in add.output
    snippet_id = _snippet_id(add.output)

    listed = _invoke(temp_dir, ["list"])
    assert listed.exit_code == 0, listed.output
    assert snippet_id[:6] in listed.output
    assert "Phase5" in listed.output

    shown = _invoke(temp_dir, ["get", snippet_id])
    assert shown.exit_code == 0, shown.output
    assert "Phase5" in shown.output
    assert "print('phase 5')" in shown.output


@pytest.mark.parametrize("provider", ["openai", "claude", "cursor", "generic"])
def test_export_each_builtin_provider_to_stdout(
    temp_dir: Path,
    mock_embeddings: Any,
    provider: str,
) -> None:
    added = _invoke(temp_dir, ["add", "x = 42", "--title", "Export Smoke", "--lang", "python"])
    assert added.exit_code == 0, added.output

    exported = _invoke(temp_dir, ["export", "--provider", provider, "--output", "-"])
    assert exported.exit_code == 0, exported.output
    assert exported.output.strip()
    assert "x = 42" in exported.output


def test_entry_point_provider_and_plugin_discovery_reaches_cli(
    temp_dir: Path,
    temp_entry_points: Any,
    fake_plugin_factory: Any,
) -> None:
    provider_ep = fake_plugin_factory(
        "e2e-provider",
        plugin_cls=FakeE2EProvider,
        group="snipcontext.providers",
    )
    plugin_ep = fake_plugin_factory("e2e-plugin", group="snipcontext.plugins")

    with temp_entry_points(
        {
            "snipcontext.providers": [provider_ep],
            "snipcontext.plugins": [plugin_ep],
        }
    ):
        providers = _invoke(temp_dir, ["providers"])
        assert providers.exit_code == 0, providers.output
        assert "e2e-provider" in providers.output
        assert "E2E fake provider" in providers.output

        plugins = _invoke(temp_dir, ["plugins", "--list"])
        assert plugins.exit_code == 0, plugins.output
        assert "e2e-plugin" in plugins.output
        assert "0.3.0" in plugins.output


def test_add_missing_content_is_helpful_error(temp_dir: Path) -> None:
    result = _invoke(temp_dir, ["add"])
    assert result.exit_code != 0
    assert "Content cannot be empty" in result.output or "No content provided" in result.output


def test_get_nonexistent_id_is_helpful_error(temp_dir: Path) -> None:
    result = _invoke(temp_dir, ["get", "missing-id"])
    assert result.exit_code != 0
    assert "Snippet not found: missing-id" in result.output


def test_export_invalid_provider_is_helpful_error(temp_dir: Path) -> None:
    result = _invoke(temp_dir, ["export", "--provider", "not-a-provider"])
    assert result.exit_code != 0
    assert "Unknown provider: not-a-provider" in result.output
    assert "Available:" in result.output
