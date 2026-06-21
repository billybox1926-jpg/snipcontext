"""Tests for the health router."""

from __future__ import annotations

from fastapi.testclient import TestClient

from snipcontext.web.app import create_app


def test_health() -> None:
    client = TestClient(create_app())
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root() -> None:
    client = TestClient(create_app())
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
