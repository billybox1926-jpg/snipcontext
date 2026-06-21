"""Tests for the snippets router."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_list_empty(client: TestClient) -> None:
    response = client.get("/snippets")
    assert response.status_code == 200
    assert response.json()["items"] == []


def test_create_and_get(client: TestClient) -> None:
    create_response = client.post(
        "/snippets",
        json={
            "title": "Test",
            "content": "print('hello')",
            "description": "demo",
            "tags": ["python"],
        },
    )
    assert create_response.status_code == 201
    snippet_id = create_response.json()["id"]

    get_response = client.get(f"/snippets/{snippet_id}")
    assert get_response.status_code == 200
    assert get_response.json()["title"] == "Test"
