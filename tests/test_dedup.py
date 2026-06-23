"""Tests for hash-based exact deduplication in `sc add`."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

from snipcontext.cli.app import app

runner = CliRunner()


def _env(tmp_path: Path, **overrides) -> dict[str, str]:
    env = {
        "SNIPCONTEXT_STORAGE__DATA_DIR": str(tmp_path),
        "SNIPCONTEXT_STORAGE__SNIPPETS_DIR": "snippets",
        "SNIPCONTEXT_STORAGE__INDEX_DIR": "index",
    }
    env.update(overrides)
    return env


def invoke_add(content: str, tmp_path: Path, input_text: str | None = None, **env_overrides):
    """Invoke `sc add` with a temporary storage directory."""
    env = _env(tmp_path, **env_overrides)
    kwargs: dict = {"env": env}
    if input_text is not None:
        kwargs["input"] = input_text
    return runner.invoke(app, ["add", content], **kwargs)


def test_hash_dedup_blocks_duplicate():
    """Adding an exact duplicate triggers the prompt and 'No' aborts."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        r1 = invoke_add("x = 42", tmp_path)
        assert r1.exit_code == 0, r1.output
        assert "Added snippet" in r1.output

        r2 = invoke_add("x = 42", tmp_path, input_text="n\n")
        assert r2.exit_code == 0
        assert "Exact duplicate of" in r2.output
        assert "Added snippet" not in r2.output


def test_hash_dedup_allows_non_duplicate():
    """Different content should not trigger the duplicate prompt."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        invoke_add("x = 42", tmp_path)
        invoke_add("y = 99", tmp_path)

        snippets = list(tmp_path.glob("snippets/*.json"))
        assert len(snippets) == 2


def test_hash_dedup_allows_explicit_yes():
    """Duplicate prompt answered 'Yes' saves the snippet anyway."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        invoke_add("x = 42", tmp_path)
        r2 = invoke_add("x = 42", tmp_path, input_text="y\n")
        assert r2.exit_code == 0, r2.output
        assert "Added snippet" in r2.output


def test_hash_dedup_skips_encrypted():
    """Encrypted snippets skip the hash dedup check."""
    pytest.importorskip("cryptography")
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        env = {
            "SNIPCONTEXT_ENCRYPT_ENABLED": "true",
            "SNIPCONTEXT_ENCRYPTION_PASSPHRASE": "unit-test-passphrase-123",
        }

        # First encrypted snippet
        r1 = runner.invoke(
            app,
            ["add", "--encrypt", "secret = 123"],
            env=_env(tmp_path, **env),
        )
        assert r1.exit_code == 0, r1.output
        assert "Added encrypted" in r1.output

        # Second encrypted snippet with identical plaintext should NOT trigger hash dedup
        r2 = runner.invoke(
            app,
            ["add", "--encrypt", "secret = 123"],
            env=_env(tmp_path, **env),
            input="n\n",
        )
        assert r2.exit_code == 0, r2.output
        assert "Exact duplicate" not in r2.output
        assert "Added encrypted" in r2.output


def test_hash_dedup_case_sensitive():
    """Hash dedup is case-sensitive (different hashes for different content)."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        invoke_add("Hello World", tmp_path)
        invoke_add("hello world", tmp_path)

        snippets = list(tmp_path.glob("snippets/*.json"))
        assert len(snippets) == 2
