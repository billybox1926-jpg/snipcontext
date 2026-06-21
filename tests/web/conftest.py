"""Fixtures for web API tests."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("uvicorn", reason="uvicorn[standard] required for web tests")

from fastapi.testclient import TestClient

from snipcontext.cli.context import reset_context
from snipcontext.web.app import create_app


@pytest.fixture(autouse=True)
def _reset() -> None:
    reset_context()
    yield
    reset_context()


@pytest.fixture
def client(tmp_path: Path):
    env = {
        "SNIPCONTEXT_STORAGE__DATA_DIR": str(tmp_path),
        "SNIPCONTEXT_STORAGE__SNIPPETS_DIR": "snippets",
        "SNIPCONTEXT_STORAGE__INDEX_DIR": "index",
    }
    old_env = os.environ.copy()
    os.environ.update(env)
    try:
        yield TestClient(create_app())
    finally:
        os.environ.clear()
        os.environ.update(old_env)
