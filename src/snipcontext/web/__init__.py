"""Web API and GUI layer for SnipContext."""

from __future__ import annotations

try:
    import fastapi  # noqa: F401
    import uvicorn  # noqa: F401
except ImportError:
    fastapi = None  # type: ignore[assignment]

WEB_AVAILABLE: bool = fastapi is not None
