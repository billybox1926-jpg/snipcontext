"""Web-facing Pydantic models for requests and responses."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str


class SnippetCreateRequest(BaseModel):
    title: str
    content: str
    description: str | None = None
    language: str | None = None
    tags: list[str] | None = None


class SnippetResponse(BaseModel):
    id: str
    title: str
    content: str | None = None
    description: str | None = None
    language: str | None = None
    tags: list[str] | None = None
    created_at: str | None = None
    updated_at: str | None = None
    metadata: dict[str, Any] | None = None


class SearchRequest(BaseModel):
    query: str
    mode: str = "hybrid"
    top_k: int = 10
    threshold: str | None = None
    fuzzy: bool = False


class ExportRequest(BaseModel):
    provider: str = "generic"
    output: str | None = None
    query: str | None = None
    ids: list[str] | None = None


class MessageResponse(BaseModel):
    type: str
    message: str


class AgentSkill(BaseModel):
    id: str
    name: str
    description: str
    input_modes: list[str] | None = None
    output_modes: list[str] | None = None


class AgentCard(BaseModel):
    name: str
    description: str
    version: str
    skills: list[AgentSkill]
    authentication: dict[str, Any] | None = None
    endpoint: str | None = None
