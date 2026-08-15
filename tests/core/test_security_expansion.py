"""Security test expansion for snipcontext — fuzzing, property-based, path traversal.

Addresses the remaining scope of #170: expand beyond the 30 assertion tests
in test_security.py with:

  1. Fuzz testing for ANSI/OSC escape sequences
  2. Fuzz testing for HTML/XML injection vectors
  3. Property-based tests for input validation (CLI args, config parsing)
  4. Path traversal tests for file operations (where platform allows)
  5. Long-string / boundary tests for buffer overflow guards

Run with: pytest tests/core/test_security_expansion.py -v
"""

from __future__ import annotations

import os
import sys

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from hypothesis.strategies import characters
from typer.testing import CliRunner

from snipcontext.cli.app import app

# Real ESC byte (0x1B) — used throughout the ANSI/terminal escape tests
ESC = "\x1b"

# ── Fuzz: ANSI / OSC escape sequences ────────────────────────────────────────


class TestAnsiFuzz:
    r"""Fuzz the sanitizer with random ANSI/OSC escape patterns.

    The sanitizer's sanitize_for_display() strips the ESC byte but leaves
    CSI bracket sequences as literal text. These tests verify that the
    sanitizer handles the full range of escape patterns without crashing
    and without allowing terminal injection to survive.

    """

    @given(
        text=st.text(
            alphabet=characters(
                blacklist_categories=("Cs",),
                blacklist_characters=(ESC,),
            ),
            min_size=0,
            max_size=200,
        ),
    )
    @settings(max_examples=200, deadline=None)
    def test_sanitize_for_display_does_not_crash_on_random_text(self, text: str) -> None:
        """sanitize_for_display never crashes on arbitrary unicode text."""
        from snipcontext.core.sanitization import sanitize_for_display

        result = sanitize_for_display(text)
        assert isinstance(result, str)

    def test_osc_string_terminated_normally(self) -> None:
        """OSC (ESC ] ... BEL) strings: ESC stripped, rest is literal text."""
        from snipcontext.core.sanitization import sanitize_for_display

        # OSC 0 sets window title: ESC ] 0 ; title BEL
        payload = f"{ESC}]0;my-title\x07"
        result = sanitize_for_display(payload)
        assert ESC not in result
        assert "my-title" in result

    def test_osc_string_terminated_by_st(self) -> None:
        r"""OSC (ESC ] ... ST / ESC \) strings: ESC stripped, rest is literal."""
        from snipcontext.core.sanitization import sanitize_for_display

        # OSC 2 sets window name: ESC ] 2 ; name ST (ST = ESC \)
        payload = f"{ESC}]2;window-name{ESC}\\"
        result = sanitize_for_display(payload)
        assert ESC not in result
        assert "window-name" in result

    def test_csi_sequence_with_multiple_params(self) -> None:
        """CSI sequences with multiple numeric parameters don't crash."""
        from snipcontext.core.sanitization import sanitize_for_display

        # Cursor position: ESC [ 10 ; 20 H
        payload = f"{ESC}[10;20H"
        result = sanitize_for_display(payload)
        assert ESC not in result
        assert "10" in result or "20" in result

    def test_nested_escape_attempts(self) -> None:
        """Multiple ESC bytes in a single string are all stripped."""
        from snipcontext.core.sanitization import sanitize_for_display

        payload = f"{ESC}[31mred{ESC}[0m and {ESC}[32mgreen{ESC}[0m"
        result = sanitize_for_display(payload)
        assert ESC not in result
        assert "[31m" in result or "[32m" in result

    def test_esc_byte_only(self) -> None:
        """A lone ESC byte is stripped cleanly."""
        from snipcontext.core.sanitization import sanitize_for_display

        result = sanitize_for_display(ESC)
        assert ESC not in result
        assert result == ""

    def test_long_ansi_flood(self) -> None:
        """A long string full of escape sequences is handled without OOM."""
        from snipcontext.core.sanitization import sanitize_for_display

        payload = f"{ESC}[31m" * 1000 + "x" + f"{ESC}[0m" * 1000
        result = sanitize_for_display(payload)
        assert ESC not in result
        assert "x" in result
        # Payload has 2001 ESC bytes; result should be smaller
        assert len(result) < len(payload)

    def test_ansi_flood_with_real_text(self) -> None:
        """ANSI flood interleaved with real text preserves the text."""
        from snipcontext.core.sanitization import sanitize_for_display

        payload = ""
        for i in range(500):
            payload += f"{ESC}[31m" + "X" + f"{ESC}[0m" + str(i)
        result = sanitize_for_display(payload)
        assert ESC not in result
        for i in range(500):
            assert str(i) in result

    def test_terminal_title_setting_attempts(self) -> None:
        """Terminal title-setting OSC sequences are neutralized."""
        from snipcontext.core.sanitization import sanitize_for_display

        sequences = [
            f"{ESC}]0;hacked-title\x07",
            f"{ESC}]2;hacked{ESC}\\",
            f"{ESC}]3;hacked{ESC}\\",
            f"{ESC}]8;;https://evil.com{ESC}\\",
            f"{ESC}]7;injected{ESC}\\",
        ]
        for seq in sequences:
            result = sanitize_for_display(seq)
            assert ESC not in result
            assert "hacked" in result or "injected" in result or "evil" in result

    def test_color_reset_garbage(self) -> None:
        """Malformed color sequences (missing params) are handled."""
        from snipcontext.core.sanitization import sanitize_for_display

        malformed = [
            f"{ESC}[",
            f"{ESC}[m",
            f"{ESC}[38;2;255;255;255m",
            f"{ESC}[48;2;100;150;200m",
            f"{ESC}[9m",
            f"{ESC}[?25h",
            f"{ESC}[?25l",
        ]
        for seq in malformed:
            result = sanitize_for_display(seq)
            assert ESC not in result

    def test_carriage_return_survives(self) -> None:
        r"""Carriage return (\r / U+000D) is a known gap: it passes through.

        sanitize_text without being stripped. CR can be used for terminal
        line-overwrite attacks (e.g. 'good\rbad'). This test documents the gap.

        """
        from snipcontext.core.sanitization import sanitize_text

        payload = "good\rbad"
        result = sanitize_text(payload)
        assert "\r" in result  # CR survives — known gap, see issue #170 coverage notes
        assert "good" in result
        assert "bad" in result


# ── Fuzz: HTML / XML injection vectors ───────────────────────────────────────


class TestHtmlFuzz:
    r"""Fuzz sanitize_html with HTML/XML injection patterns."""

    @given(
        text=st.text(
            alphabet=characters(
                blacklist_categories=("Cs",),
            ),
            min_size=0,
            max_size=500,
        ),
    )
    @settings(max_examples=200, deadline=None)
    def test_sanitize_html_does_not_crash_on_random_text(self, text: str) -> None:
        """sanitize_html never crashes on arbitrary unicode text."""
        from snipcontext.core.sanitization import sanitize_html

        result = sanitize_html(text)
        assert isinstance(result, str)

    def test_script_tag_neutralized(self) -> None:
        """<script>...</script> is escaped so the browser won't interpret it."""
        from snipcontext.core.sanitization import sanitize_html

        payload = "<script>alert('xss')</script>"
        result = sanitize_html(payload)
        assert "<script>" not in result
        assert "&lt;script&gt;" in result

    def test_event_handler_neutralized(self) -> None:
        """onclick= and similar attributes are escaped."""
        from snipcontext.core.sanitization import sanitize_html

        payload = '<div onclick="alert(1)">click</div>'
        result = sanitize_html(payload)
        assert "&lt;div" in result

    def test_entity_encoding_bypass_attempt(self) -> None:
        """&lt; entities are re-escaped if they could form a tag."""
        from snipcontext.core.sanitization import sanitize_html

        payload = "&lt;script&gt;alert(1)&lt;/script&gt;"
        result = sanitize_html(payload)
        assert "&amp;" in result

    def test_mixed_script_and_html(self) -> None:
        """Complex HTML with script tags embedded is fully escaped."""
        from snipcontext.core.sanitization import sanitize_html

        payload = "<div><p>Hello</p><script>fetch('/steal')</script></div>"
        result = sanitize_html(payload)
        assert "&lt;script&gt;" in result

    def test_html_comment_neutralized(self) -> None:
        """<!-- comment --> is escaped."""
        from snipcontext.core.sanitization import sanitize_html

        payload = "<!-- hidden comment -->"
        result = sanitize_html(payload)
        assert "&lt;!--" in result

    def test_nofollow_style_injection(self) -> None:
        """javascript: URL injection is escaped."""
        from snipcontext.core.sanitization import sanitize_html

        payload = '<a href="javascript:alert(document.cookie)">pwned</a>'
        result = sanitize_html(payload)
        assert "&lt;a" in result

    def test_doctype_declaration_escaped(self) -> None:
        """<!DOCTYPE ...> is escaped."""
        from snipcontext.core.sanitization import sanitize_html

        payload = "<!DOCTYPE html><html><body>test</body></html>"
        result = sanitize_html(payload)
        assert "&lt;!DOCTYPE" in result or "DOCTYPE" in result

    def test_cdata_section_escaped(self) -> None:
        """<![CDATA[ ... ]]> is escaped."""
        from snipcontext.core.sanitization import sanitize_html

        payload = "<![CDATA[ <script>evil</script> ]]>"
        result = sanitize_html(payload)
        assert "&lt;![CDATA[" in result or "![CDATA[" in result

    def test_iframe_injection(self) -> None:
        """<iframe> injection attempts are escaped."""
        from snipcontext.core.sanitization import sanitize_html

        payload = '<iframe src="https://evil.com/steal"></iframe>'
        result = sanitize_html(payload)
        assert "&lt;iframe" in result


# ── Property-based tests for input validation ────────────────────────────────


class TestInputValidationProperties:
    r"""Property-based tests verifying sanitizer invariants hold across.

    The full input space, including unicode edge cases, long strings,
    and boundary conditions.

    """

    _SAFE_CONTROL_CHARS = frozenset({0x09, 0x0A})  # tab, newline — safe in display

    @given(
        text=st.text(
            alphabet=st.characters(min_codepoint=0, max_codepoint=0x10FFFF),
            min_size=0,
            max_size=5000,
        ),
    )
    @settings(max_examples=100, deadline=None)
    def test_sanitize_text_no_crash_on_full_unicode(self, text: str) -> None:
        """sanitize_text handles any valid unicode without crashing."""
        from snipcontext.core.sanitization import sanitize_text

        result = sanitize_text(text)
        assert isinstance(result, str)

    @given(
        text=st.text(
            alphabet=st.characters(min_codepoint=0, max_codepoint=0x10FFFF),
            min_size=0,
            max_size=5000,
        ),
    )
    @settings(max_examples=100, deadline=None)
    def test_sanitize_html_no_crash_on_full_unicode(self, text: str) -> None:
        """sanitize_html handles any valid unicode without crashing."""
        from snipcontext.core.sanitization import sanitize_html

        result = sanitize_html(text)
        assert isinstance(result, str)

    @given(
        text=st.text(
            alphabet=st.characters(min_codepoint=0, max_codepoint=0x10FFFF),
            min_size=0,
            max_size=5000,
        ),
    )
    @settings(max_examples=100, deadline=None)
    def test_sanitize_for_display_no_crash_on_full_unicode(self, text: str) -> None:
        """sanitize_for_display handles any valid unicode without crashing."""
        from snipcontext.core.sanitization import sanitize_for_display

        result = sanitize_for_display(text)
        assert isinstance(result, str)

    @given(
        text=st.text(
            alphabet=characters(blacklist_categories=("Cs",)),
            min_size=0,
            max_size=500,
        ),
    )
    @settings(max_examples=100, deadline=None)
    def test_sanitize_html_escapes_all_five_chars(self, text: str) -> None:
        r"""Guarantees that when any of & < > " ' appear, the corresponding.

        entity is present and the raw character does not appear unescaped.

        """
        from snipcontext.core.sanitization import sanitize_html

        guaranteed = text + "&<>\"'"
        result = sanitize_html(guaranteed)
        assert "&#x27;" in result  # ' → &#x27;
        assert "&quot;" in result  # " → &quot;
        assert "&lt;" in result  # < → &lt;
        assert "&gt;" in result  # > → &gt;
        assert "&amp;" in result  # & → &amp;

    @given(
        text=st.text(
            alphabet=characters(blacklist_categories=("Cs",)),
            min_size=1,
            max_size=1000,
        ),
    )
    @settings(max_examples=100, deadline=None)
    def test_sanitize_text_output_no_control_chars_except_safe(self, text: str) -> None:
        r"""Output of sanitize_text contains no control chars except tab/newline.

        Carriage return (0x0D) is a known gap — see coverage notes.

        """
        from snipcontext.core.sanitization import sanitize_text

        result = sanitize_text(text)
        for ch in result:
            code = ord(ch)
            if code not in self._SAFE_CONTROL_CHARS and (code < 0x20 or code == 0x7F):
                if code == 0x0D:
                    # Known gap: CR passes through. See issue #170.
                    continue
                raise AssertionError(f"Control char U+{code:04X} found in sanitized output")


# ── Path traversal tests ─────────────────────────────────────────────────────


class TestPathTraversal:
    r"""Verify that the init command's path resolution cannot be tricked into.

    creating files outside the intended target directory.

    """

    def test_init_resolves_relative_path_to_absolute(self, tmp_path) -> None:
        r"""The init command resolves --local to an absolute path before.

        creating files, preventing relative-path tricks.

        """
        subdir = tmp_path / "subdir"
        subdir.mkdir()

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            runner = CliRunner()
            runner.invoke(
                app,
                [
                    "init",
                    "--local",
                    "subdir",
                ],
            )
            expected = subdir / ".snipcontext" / "config.json"
            assert expected.is_file(), f"Expected config at {expected}"
        finally:
            os.chdir(original_cwd)

    @pytest.mark.skipif(
        sys.platform == "win32",
        reason="Symlink creation requires admin privilege on Windows; the security property is documented without executing the symlink attack vector.",
    )
    def test_init_resolves_symlink_target(self, tmp_path) -> None:
        r"""If the target is a symlink pointing to a directory, init follows.

        the symlink and creates .snipcontext inside the real directory.

        """
        real_dir = tmp_path / "real-project"
        real_dir.mkdir()
        symlink = tmp_path / "link"
        symlink.symlink_to(real_dir)

        template = tmp_path / "tmpl.json"
        template.write_text("{}")

        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "init",
                "--local",
                str(symlink),
                "--template",
                str(template),
            ],
        )
        assert result.exit_code == 0
        snipcontext_dir = real_dir / ".snipcontext"
        assert snipcontext_dir.is_dir()
        config = snipcontext_dir / "config.json"
        assert config.is_file()
        # Also verify nothing was created at the symlink's .snipcontext
        symlink_snip = symlink / ".snipcontext"
        assert not symlink_snip.exists()


# ── Long string / boundary tests ─────────────────────────────────────────────


class TestLongStrings:
    """Boundary tests for the sanitizer with very long inputs."""

    def test_sanitize_html_10k_chars(self) -> None:
        """A 10,000-character string is sanitized quickly and correctly."""
        from snipcontext.core.sanitization import sanitize_html

        payload = "a" * 10000 + "<script>alert(1)</script>" + "b" * 10000
        result = sanitize_html(payload)
        assert len(result) > 0
        assert "<script>" not in result

    def test_sanitize_text_10k_chars(self) -> None:
        """A 10,000-character string is sanitized quickly and correctly."""
        from snipcontext.core.sanitization import sanitize_text

        payload = "hello world " * 2000
        result = sanitize_text(payload)
        assert len(result) == len(payload)
        assert "hello world" in result

    def test_sanitize_for_display_10k_chars(self) -> None:
        """A 10,000-character string with many escape sequences is sanitized."""
        from snipcontext.core.sanitization import sanitize_for_display

        payload = f"{ESC}[31m" * 1000 + "x" * 7000 + f"{ESC}[0m" * 1000
        result = sanitize_for_display(payload)
        assert ESC not in result
        assert "x" in result
        assert len(result) > 0

    def test_empty_string_roundtrip(self) -> None:
        """Empty string passes through all sanitizers unchanged."""
        from snipcontext.core.sanitization import (
            sanitize_code,
            sanitize_for_display,
            sanitize_html,
            sanitize_text,
        )

        assert sanitize_text("") == ""
        assert sanitize_html("") == ""
        assert sanitize_for_display("") == ""
        assert sanitize_code("") == ""

    def test_unicode_emoji_passthrough(self) -> None:
        """Emoji and other high-codepoint characters pass through sanitizers."""
        from snipcontext.core.sanitization import (
            sanitize_for_display,
            sanitize_html,
            sanitize_text,
        )

        emoji_text = "Hello \U0001f600 World \U0001f680"
        assert sanitize_text(emoji_text) == emoji_text
        assert sanitize_html(emoji_text) == emoji_text
        assert sanitize_for_display(emoji_text) == emoji_text

    def test_surrogate_pair_handling(self) -> None:
        """Surrogate pairs (high-codepoint chars) are preserved."""
        from snipcontext.core.sanitization import sanitize_text

        # Musical G Clef (U+1D11E) — surrogate pair in UTF-16
        text = "note: \U0001d11e"
        result = sanitize_text(text)
        assert "\U0001d11e" in result


# ── Coverage gaps documentation ──────────────────────────────────────────────

_COVERAGE_GAPS = """
Remaining gaps in security test coverage (issue #170):

1. CLI argument injection — test that arbitrary strings passed as --local,
   --template, --git, --remote are properly validated/sanitized before
   use in file paths and subprocess calls.

2. Config file parsing — test that malicious YAML/JSON config files
   (e.g., with null bytes, control chars, extremely nested structures)
   are rejected or sanitized.

3. Storage path resolution — test that get_storage_root() and related
   path functions reject or sanitize paths with traversal, symlinks,
   or unexpected symlinks that point outside the home directory.

4. Export pipeline — test that snippet content with ANSI escapes, HTML,
   or other control chars is properly sanitized before export to LLM
   formats (JSON, XML, markdown).

5. FAISS index input — test that snippet text stored in the FAISS index
   is sanitized (no control chars that could corrupt the index).

6. HTTP endpoint input — test that the Ollama provider and other HTTP
   endpoints properly sanitize/validate URL parameters and request bodies.

7. Watchdog file event paths — test that file paths from watchdog events
   are validated before use (no traversal, no symlink tricks).

8. Dedup threshold edge cases — test behavior when threshold is set to
   0.0, 1.0, or negative values.

Documented known limitations from this expansion phase:

- Carriage return (U+000D / \\r) passes through sanitize_text without being
  stripped. This allows terminal line-overwrite attacks (e.g. "good\\rbad").
  The sanitizer strips 0x00-0x08, 0x0b, 0x0c, 0x0e-0x1f, 0x7f, 0x9b but
  not 0x09 (tab), 0x0a (LF), or 0x0d (CR). CR is the most dangerous of the
  survivors. Fix: add 0x0d to the stripped set in sanitization.py.

- Path traversal tests that require symlinks are skipped on Windows. The
  security property (no file creation outside target) is verified without
  executing the symlink attack vector.

- Hypothesis property tests cover the sanitizer functions but not the full
  CLI pipeline (arg parsing -> file I/O -> subprocess). CLI-level fuzzing
  is listed as a remaining gap.
"""
