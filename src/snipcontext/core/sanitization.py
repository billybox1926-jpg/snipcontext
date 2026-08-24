"""Sanitization utilities for snippet content and metadata.

Prevents injection attacks across all output surfaces:
- Markdown/HTML injection in export providers
- Terminal escape sequence injection via Rich
- Code fence breakout in markdown exports

All public functions are pure and allocation-cheap for the common case
(no dangerous characters present).
"""

from __future__ import annotations

import re

# Control characters that can be used for terminal escape injection
# (ANSI escapes, OSC/DCS sequences, C1 controls).
# Covers the full C1 range (\x80-\x9f) plus DEL (\x7f) and C0 controls,
# so 8-bit DCS (\x90) and OSC (\x9d) can no longer slip through.
_CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f\x80-\x9f]")

# Unicode bidirectional override characters (U+202A–U+202E, U+2066–U+2069).
# Used in "Trojan Source" attacks to spoof code display order.
_BIDI_CHAR_RE = re.compile(r"[\u202a-\u202e\u2066-\u2069]")

# Rich markup injection — [ and ] are interpreted as Rich tags
# https://rich.readthedocs.io/en/latest/markup.html
_RICH_MARKUP_RE = re.compile(r"\[([^\]]*)\]")

# Characters with special meaning in HTML / XML contexts
HTML_ESCAPE_TABLE: dict[str, str] = {
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#x27;",
}


def sanitize_text(text: str) -> str:
    """Strip control characters and Rich markup from plain-text fields.

    Used for titles, descriptions, tags, and other metadata that is
    output in contexts where Rich markup or terminal escapes could be
    interpreted.

    Returns the original string unchanged if no dangerous characters
    are found (fast path).
    """
    if not text:
        return text

    # Fast path: no control chars, no Rich markup brackets, no bidi overrides
    if (
        not _CONTROL_CHAR_RE.search(text)
        and not _BIDI_CHAR_RE.search(text)
        and "[" not in text
    ):
        return text

    # Remove control characters first
    cleaned = _CONTROL_CHAR_RE.sub("", text)
    # Remove Unicode bidi override characters (Trojan Source defense)
    cleaned = _BIDI_CHAR_RE.sub("", cleaned)
    # Neutralize Rich [tag] syntax by inserting zero-width space
    # between the brackets so Rich won't parse it as markup
    cleaned = cleaned.replace("[", "[[]")
    return cleaned


def sanitize_html(text: str) -> str:
    """Escape HTML-sensitive characters (& < > " ') for XML/HTML contexts.

    This is the sanitization layer for providers that produce XML/HTML
    output (Claude XML provider).  For plain-text / Markdown contexts
    use :func:`sanitize_code` instead.
    """
    if not text:
        return text
    # Use str.translate for the fast path of single-char replacements
    for char, replacement in HTML_ESCAPE_TABLE.items():
        if char in text:
            text = text.replace(char, replacement)
    return text


def sanitize_code(content: str) -> str:
    """Prevent markdown code-fence breakout and strip control characters.

    If the content itself contains `` ``` `` (possibly with a language
    hint like `` ```python ``), wrapping it naively in a fenced code
    block lets the inner fence close the block early.

    We escape opening code-fence sequences by inserting a zero-width
    space after the opening backticks so they are rendered literally.

    Control characters (including ANSI escape sequences and C1 8-bit
    escapes like DCS/OSC) are also stripped to prevent terminal injection
    when output is printed directly. Unicode bidi override characters
    are removed to prevent "Trojan Source" display spoofing.
    """
    if not content:
        return content

    # Strip control characters (terminal escape injection)
    if _CONTROL_CHAR_RE.search(content):
        content = _CONTROL_CHAR_RE.sub("", content)

    # Remove Unicode bidi override characters (Trojan Source defense)
    if _BIDI_CHAR_RE.search(content):
        content = _BIDI_CHAR_RE.sub("", content)

    # Break code-fence injection: escape opening ``` sequences
    # that appear at the start of a line or after whitespace.
    # We insert a zero-width space so the fence is not recognized.
    if "```" in content:
        content = content.replace("```", "`\u200b``")

    return content


def sanitize_for_display(content: str) -> str:
    """Prepare snippet content for direct terminal display.

    Removes ANSI escape sequences, C1 8-bit escapes, other control
    characters, and Unicode bidi overrides that could be interpreted
    by the terminal emulator or spoof code display order.
    """
    if not content:
        return content
    cleaned = _CONTROL_CHAR_RE.sub("", content)
    return _BIDI_CHAR_RE.sub("", cleaned)
