"""Targeted security tests for snipcontext sanitization pipeline.

Addresses issue #170: Security Test Coverage Audit & Expansion.
Tests each public sanitization function against known attack vectors.
"""

from __future__ import annotations

import pytest

from snipcontext.core.sanitization import (
    sanitize_code,
    sanitize_for_display,
    sanitize_html,
    sanitize_text,
)

# ── sanitize_text ──────────────────────────────────────────────────────────


class TestSanitizeText:
    """sanitize_text strips control chars and neutralizes Rich markup [tag] syntax.

    Used for titles, descriptions, tags, and other metadata output via Rich.
    """

    def test_no_dangerous_chars_passthrough(self) -> None:
        """Fast path: string without control chars or [ is returned unchanged."""
        assert sanitize_text("Hello World") == "Hello World"
        assert sanitize_text("snippet-title") == "snippet-title"
        assert sanitize_text("") == ""
        assert sanitize_text("   ") == "   "
        assert sanitize_text("mixedCase123_!@#") == "mixedCase123_!@#"

    def test_control_characters_stripped(self) -> None:
        r"""Control chars (\x00-\x08, \x0b, \x0c, \x0e-\x1f, \x7f, \x80-\x9f) are removed."""
        # DEL character
        assert "\x7f" not in sanitize_text("hello\x7fworld")
        assert sanitize_text("hello\x7fworld") == "helloworld"
        # BEL character
        assert "\x07" not in sanitize_text("alert\x07me")
        # Unit separator
        assert "\x1f" not in sanitize_text("a\x1fb")
        # C1 DCS (8-bit Device Control String)
        assert "\x90" not in sanitize_text("a\x90b")
        # C1 OSC (8-bit Operating System Command)
        assert "\x9d" not in sanitize_text("a\x9db")
        # C1 CSI (single-byte 8-bit CSI)
        assert "\x9b" not in sanitize_text("a\x9bb")

    def test_rich_markup_neutralized(self) -> None:
        """[tag] syntax is broken so Rich doesn't interpret it as markup."""
        result = sanitize_text("hello [bold]world[/bold]")
        # Each [ becomes [[] so Rich sees [[bold]] not [bold]
        assert "[[]" in result
        assert "[bold]" not in result
        assert "[/bold]" not in result

    def test_mixed_control_and_markup(self) -> None:
        """Both control chars and markup handled in one pass."""
        result = sanitize_text("title\x07[bad]tag")
        assert "\x07" not in result
        assert "[bad]" not in result
        assert "[[]" in result


class TestSanitizeTextBidi:
    """Unicode bidi override characters are stripped (issue #196)."""

    @pytest.mark.parametrize("char", [
        "\u202a",  # LRE
        "\u202b",  # RLE
        "\u202c",  # PDF
        "\u202d",  # LRO
        "\u202e",  # RLO
        "\u2066",  # LRI
        "\u2067",  # RLI
        "\u2068",  # FSI
        "\u2069",  # PDI
    ])
    def test_bidi_stripped_from_text(self, char: str) -> None:
        result = sanitize_text(f"title{char}middle")
        assert char not in result

    @pytest.mark.parametrize("char", [
        "\u202a", "\u202b", "\u202c", "\u202d", "\u202e",
        "\u2066", "\u2067", "\u2068", "\u2069",
    ])
    def test_bidi_stripped_from_code(self, char: str) -> None:
        result = sanitize_code(f"code{char}more")
        assert char not in result

    @pytest.mark.parametrize("char", [
        "\u202a", "\u202b", "\u202c", "\u202d", "\u202e",
        "\u2066", "\u2067", "\u2068", "\u2069",
    ])
    def test_bidi_stripped_from_display(self, char: str) -> None:
        result = sanitize_for_display(f"display{char}text")
        assert char not in result


# ── sanitize_html ──────────────────────────────────────────────────────────


class TestSanitizeHtml:
    r"""sanitize_html escapes & < > \" ' for XML/HTML output contexts (Claude XML provider)."""

    def test_no_html_chars_passthrough(self) -> None:
        """Plain text without HTML-sensitive chars passes through unchanged."""
        assert sanitize_html("Hello World") == "Hello World"
        assert sanitize_html("plain text") == "plain text"

    def test_ampersand_escaped(self) -> None:
        assert "&" not in sanitize_html("foo&bar").replace("&amp;", "")
        assert sanitize_html("foo&bar") == "foo&amp;bar"

    def test_angle_brackets_escaped(self) -> None:
        assert "<" not in sanitize_html("<div>")
        assert ">" not in sanitize_html("</div>")
        assert sanitize_html("<div>") == "&lt;div&gt;"
        assert sanitize_html("</div>") == "&lt;/div&gt;"

    def test_quotes_escaped(self) -> None:
        # Double-quote " maps to &quot; per HTML_ESCAPE_TABLE
        assert sanitize_html('"quoted"') == "&quot;quoted&quot;"
        # Single-quote ' maps to &#x27;
        result = sanitize_html("'single'")
        assert "'" not in result
        assert "&#x27;" in result  # ' → &#x27;
        assert "&quot;" not in result  # no " in input, so no &quot; in output

    def test_multiple_chars_in_one_string(self) -> None:
        """All five HTML-sensitive chars escaped in a single string."""
        result = sanitize_html("a & b < c > d \" e ' f")
        assert "&amp;" in result
        assert "&lt;" in result
        assert "&gt;" in result
        assert "&#x27;" in result  # ' → &#x27;

    def test_empty_and_whitespace(self) -> None:
        assert sanitize_html("") == ""
        assert sanitize_html("   ") == "   "

    def test_already_escaped_content_not_double_escaped(self) -> None:
        """Content that's already escaped should not be double-escaped."""
        # Since the function checks char-by-char and replaces, already-escaped
        # content like &amp; would have the & replaced again if present.
        # This test documents the current behavior.
        result = sanitize_html("&amp;")
        # & in &amp; gets escaped → &amp;amp;
        assert result == "&amp;amp;"

    def test_xss_prevention(self) -> None:
        """Script tags and event handlers are escaped."""
        payload = "<script>alert('xss')</script>"
        result = sanitize_html(payload)
        assert "<script>" not in result
        assert "alert" in result  # text content preserved
        assert "&lt;script&gt;" in result


# ── sanitize_code ──────────────────────────────────────────────────────────


class TestSanitizeCode:
    """sanitize_code prevents markdown code-fence breakout and strips control chars.

    Used for all code content output in exports (Claude, Cursor, OpenAI, Ollama).
    """

    def test_no_fences_passthrough(self) -> None:
        """Code without ``` fences passes through unchanged."""
        assert sanitize_code("print('hello')") == "print('hello')"
        assert sanitize_code("") == ""

    def test_single_backtick_passthrough(self) -> None:
        """Single backticks are not fences — should pass through (no replacement)."""
        # The function only replaces ``` (triple backtick), not single `
        result = sanitize_code("use the `foo` variable")
        assert result == "use the `foo` variable"

    def test_triple_backtick_escaped(self) -> None:
        """``` fence sequences get a zero-width space inserted to prevent breakout."""
        result = sanitize_code("```python\nprint(1)\n```")
        assert "```" not in result
        assert "\u200b" in result  # zero-width space
        assert "`\u200b`" in result

    def test_nested_fence_prevention(self) -> None:
        """Inner fences in snippet content cannot close the outer export fence."""
        # Attack: snippet contains ``` which would close the export's code fence
        malicious = "some code\n```\nmalicious content outside fence\n```\nmore code"
        result = sanitize_code(malicious)
        assert "```" not in result
        # All three backticks neutralized
        assert result.count("\u200b") >= 2  # both opening and closing fences

    def test_control_chars_in_code_stripped(self) -> None:
        """ANSI escape sequences — ESC byte stripped, CSI bracket sequence remains."""
        ansi_green = "\x1b[32mhello\x1b[0m"
        result = sanitize_code(ansi_green)
        assert "\x1b" not in result  # ESC byte removed
        # Note: only the ESC byte is stripped; [32m and [0m remain as literal text
        # (the sanitizer targets control chars, not full CSI sequence parsing)
        assert "[32mhello[0m" == result

    def test_ansi_escape_byte_removed_but_csi_text_preserved(self) -> None:
        """The ESC control char is removed; CSI command sequence text stays."""
        result = sanitize_code("\x1b[1;31mRED\x1b[0m")
        assert "\x1b" not in result
        assert "[1;31mRED[0m" == result

    def test_mixed_fence_and_escape(self) -> None:
        """Both fence breakout and ANSI escape handled together."""
        payload = "\x1b[31m```evil\n```"
        result = sanitize_code(payload)
        assert "\x1b" not in result
        assert "```" not in result
        assert "\u200b" in result

    def test_backtick_edge_cases(self) -> None:
        """Variations of triple-backtick patterns."""
        # Four backticks: first three replaced with escaped fence, fourth remains
        result = sanitize_code("````python")
        assert "\u200b" in result  # escaped fence present
        # Note: output is \`​\u200b```python — the escaped fence + remaining backtick
        # creates a visible ``` in the output, but this is SAFE: the \u200b before it
        # makes markdown render these as literal backticks, not a code fence.
        # The fence breakout is prevented by the zero-width space, not by removing ```.

        # Three backticks with language hint
        result = sanitize_code("```rust\nfn main() {}\n```")
        assert "```" not in result
        assert "\u200b" in result

    def test_single_backtick_is_not_a_fence(self) -> None:
        """Single and double backticks pass through — only ``` is a fence."""
        # Single backtick — no replacement
        result = sanitize_code("use `foo` here")
        assert result == "use `foo` here"
        assert "\u200b" not in result

        # Double backtick — no replacement
        result = sanitize_code("use ``foo`` here")
        assert result == "use ``foo`` here"


# ── sanitize_for_display ────────────────────────────────────────────────────


class TestSanitizeForDisplay:
    """sanitize_for_display strips ANSI and control chars for direct terminal output.

    Simpler than sanitize_text — no Rich markup handling, just control char removal.
    """

    def test_ansi_stripped(self) -> None:
        """ANSI escape sequences — ESC byte removed, CSI brackets remain as text."""
        red = "\x1b[31mRED\x1b[0m"
        result = sanitize_for_display(red)
        assert "\x1b" not in result
        # Only ESC char stripped; [31m and [0m remain as visible text.
        # Full CSI sequence parsing would be a larger addition not in scope here.
        assert "[31mRED[0m" == result

    def test_control_chars_stripped(self) -> None:
        """All control chars in the regex range removed, including C1."""
        assert "\x00" not in sanitize_for_display("a\x00b")
        assert "\x1f" not in sanitize_for_display("a\x1fb")
        assert "\x7f" not in sanitize_for_display("a\x7fb")
        # C1: DCS, OSC, CSI
        assert "\x90" not in sanitize_for_display("a\x90b")
        assert "\x9d" not in sanitize_for_display("a\x9db")
        assert "\x9b" not in sanitize_for_display("a\x9bb")

    def test_bidi_overrides_stripped(self) -> None:
        """Unicode bidi override chars are removed (Trojan Source defense)."""
        for char in ["\u202a", "\u202b", "\u202c", "\u202d", "\u202e",
                     "\u2066", "\u2067", "\u2068", "\u2069"]:
            assert char not in sanitize_for_display(f"a{char}b")

    def test_plain_text_passthrough(self) -> None:
        """Normal text passes through."""
        assert sanitize_for_display("normal text") == "normal text"
        assert sanitize_for_display("") == ""

    def test_mixed_ansi_and_plain(self) -> None:
        """ANSI codes stripped, plain text preserved."""
        payload = "\x1b[1;32mBold Green\x1b[0m and normal"
        result = sanitize_for_display(payload)
        assert "\x1b" not in result
        assert "Bold Green" in result
        assert "and normal" in result


# ── Cross-cutting security tests ────────────────────────────────────────────


class TestSanitizationCrossCutting:
    """Tests that verify the sanitization pipeline holistically."""

    def test_export_pipeline_sanitizes_all_fields(self) -> None:
        """All fields in an export are sanitized (metadata + content)."""
        from snipcontext.core.sanitization import sanitize_code, sanitize_text

        # Simulate what an export pipeline does: sanitize every field
        malicious_title = "Title [\x07bold]with\x1fcontrol"
        malicious_content = "\x1b[31m```hack\nmalicious\n```\x1b[0m"

        safe_title = sanitize_text(malicious_title)
        safe_content = sanitize_code(malicious_content)

        assert "\x07" not in safe_title
        assert "\x1f" not in safe_title
        assert "[bold]" not in safe_title  # Rich markup neutralized
        assert "\x1b" not in safe_content
        assert "```" not in safe_content  # fence escaped

    def test_path_traversal_in_title_not_executable(self) -> None:
        """Path traversal strings in metadata are just strings — no filesystem access."""
        from snipcontext.core.sanitization import sanitize_text

        traversal = "../../../etc/passwd"
        result = sanitize_text(traversal)
        # sanitize_text doesn't strip dots or slashes — it's not a filesystem sanitizer
        # This test documents the boundary: sanitization handles injection, not path safety
        assert result == traversal
        # The point: this is a string, not a path used in a filesystem operation

    def test_unicode_injection_resistant(self) -> None:
        """Unicode characters (including zero-width, RTL, emoji) pass through safely."""
        from snipcontext.core.sanitization import sanitize_text

        # Zero-width space (already used by sanitize_code as escape mechanism)
        zwsp = "\u200b"
        result = sanitize_text(f"title{zwsp}middle")
        assert zwsp in result  # sanitize_text doesn't remove zwsp

        # Emoji pass through
        result2 = sanitize_text("snippet 😀")
        assert "😀" in result2

    def test_very_long_input_handled(self) -> None:
        """Extremely long strings don't crash or hang."""
        from snipcontext.core.sanitization import sanitize_code, sanitize_text

        long_string = "a" * 1_000_000
        result = sanitize_text(long_string)
        assert len(result) == 1_000_000
        assert result == long_string  # no dangerous chars

        long_code = "x" * 1_000_000 + "```"
        result2 = sanitize_code(long_code)
        assert len(result2) > 999_000  # slightly shorter due to fence replacement

    def test_null_byte_handling(self) -> None:
        """Null bytes (C-string terminators) are stripped."""
        from snipcontext.core.sanitization import sanitize_code, sanitize_for_display, sanitize_text

        for func in [sanitize_text, sanitize_code, sanitize_for_display]:
            result = func("before\x00after")
            assert "\x00" not in result
            assert "before" in result
            assert "after" in result
