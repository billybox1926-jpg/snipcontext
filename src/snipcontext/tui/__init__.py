"""SnipContext TUI (Textual-based terminal UI)."""

from __future__ import annotations

__all__ = ["run_tui"]

try:  # Optional: only required for the Textual browser
    from snipcontext.tui.textual_app import run_tui  # noqa: F401
except Exception:  # pragma: no cover - optional dependency fallback
    run_tui = None  # type: ignore[assignment,misc]
