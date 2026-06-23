"""Tests for the A2A Agent Card endpoint and CLI."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient
from typer.testing import CliRunner

from snipcontext import __version__
from snipcontext.cli.app import app
from snipcontext.web.app import create_app


def test_agent_card_endpoint() -> None:
    client = TestClient(create_app())
    response = client.get("/.well-known/agent.json")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "SnipContext"
    assert "version" in data
    assert data["version"] == __version__
    assert "skills" in data
    assert len(data["skills"]) >= 4


def test_agent_card_skills() -> None:
    client = TestClient(create_app())
    response = client.get("/.well-known/agent.json")
    data = response.json()
    skill_ids = [s["id"] for s in data["skills"]]
    assert "search" in skill_ids
    assert "store" in skill_ids
    assert "export" in skill_ids
    assert "stats" in skill_ids


def test_agent_card_endpoint_field() -> None:
    client = TestClient(create_app())
    response = client.get("/.well-known/agent.json")
    data = response.json()
    assert "endpoint" in data
    assert data["endpoint"].startswith("http://")


def test_agent_card_cli() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["agent-card"])
    assert result.exit_code == 0, result.stdout + result.stderr
    data = json.loads(result.stdout)
    assert data["name"] == "SnipContext"
    assert "version" in data
    assert data["version"] == __version__
