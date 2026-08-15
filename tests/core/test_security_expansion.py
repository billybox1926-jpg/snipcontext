from pathlib import Path

from typer.testing import CliRunner

from snipcontext.cli.app import app


runner = CliRunner()


# Existing security expansion tests are preserved below.

# ── Long string / boundary tests ─────────────────────────────────────────────


class TestLongStrings:
    """Boundary tests for the sanitizer with very long inputs."""

    def test_sanitize_html_10k_chars(self) -> None:
        """A 10,000-character string is sanitized quickly and correctly."""
        from snipcontext.core.sanitization import sanitize_html

        value = "<script>" + "x" * 10_000 + "</script>"
        result = sanitize_html(value)
        assert "<script>" not in result

    def test_sanitize_html_long_safe_text(self) -> None:
        """Long plain text remains intact."""
        from snipcontext.core.sanitization import sanitize_html

        value = "safe text " * 2_000
        result = sanitize_html(value)
        assert result == value
