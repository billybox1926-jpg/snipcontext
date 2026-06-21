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
# (ANSI escapes, OSC sequences, etc.)
_CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f\x9b]")

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

    # Fast path: no control chars and no Rich markup brackets
    if not _CONTROL_CHAR_RE.search(text) and "[" not in text:
        return text

    # Remove control characters first, then escape Rich markup
    cleaned = _CONTROL_CHAR_RE.sub("", text)
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

    Control characters (including ANSI escape sequences) are also
    stripped to prevent terminal injection when output is printed
    directly.
    """
    if not content:
        return content

    # Strip control characters (terminal escape injection)
    if _CONTROL_CHAR_RE.search(content):
        content = _CONTROL_CHAR_RE.sub("", content)

    # Break code-fence injection: escape opening ``` sequences
    # that appear at the start of a line or after whitespace.
    # We insert a zero-width space so the fence is not recognized.
    if "```" in content:
        content = content.replace("```", "`\u200b``")

    return content


def sanitize_for_display(content: str) -> str:
    """Prepare snippet content for direct terminal display.

    Removes ANSI escape sequences and other control characters
    that could be interpreted by the terminal emulator.
    """
    if not content:
        return content
    return _CONTROL_CHAR_RE.sub("", content)
