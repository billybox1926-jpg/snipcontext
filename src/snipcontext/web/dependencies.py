"""Shared FastAPI dependencies."""

from __future__ import annotations

from typing import Any

_storage: Any | None = None


def bootstrap_storage(storage: Any) -> None:
    global _storage
    _storage = storage


def get_storage() -> Any:
    if _storage is None:
        from snipcontext.cli.context import get_context as _get_context

        _ctx = _get_context()
        return _ctx[1]
    return _storage
