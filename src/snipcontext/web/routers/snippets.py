"""Snippets router."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from snipcontext.core.snippet_ops import (
    create_snippet,
    delete_snippet,
    edit_snippet,
    get_snippet,
    list_snippets,
)
from snipcontext.web.dependencies import get_storage
from snipcontext.web.schemas import SnippetCreateRequest, SnippetResponse

router = APIRouter()


@router.get("/snippets")  # type: ignore[untyped-decorator]
async def list_snippet_items(
    storage: Any = None,
) -> dict[str, Any]:
    storage = get_storage()
    items = list_snippets(storage)
    return {
        "items": [
            {
                "id": getattr(item, "id", ""),
                "title": getattr(item.metadata, "title", ""),
                "language": getattr(item.metadata.language, "value", ""),
                "tags": getattr(item.metadata, "tags", []),
                "updated_at": getattr(item.metadata, "updated_at", ""),
            }
            for item in items
        ]
    }


@router.post("/snippets", response_model=SnippetResponse, status_code=201)  # type: ignore[untyped-decorator]
async def create_snippet_item(
    body: SnippetCreateRequest,
    storage: Any = None,
) -> SnippetResponse:
    storage = get_storage()
    snippet = create_snippet(
        content=body.content,
        title=body.title,
        description=body.description or "",
        language=body.language or "",
        tags=body.tags or [],
    )
    storage.save(snippet)
    return SnippetResponse(
        id=snippet.id,
        title=snippet.metadata.title,
        content=snippet.content,
        description=snippet.metadata.description,
        language=snippet.metadata.language.value,
        tags=snippet.tags,
        created_at=snippet.created_at.isoformat(),
        updated_at=snippet.updated_at.isoformat(),
        metadata=snippet.metadata.model_dump()
        if hasattr(snippet.metadata, "model_dump")
        else snippet.metadata.__dict__,
    )


@router.get("/snippets/{snippet_id}", response_model=SnippetResponse)  # type: ignore[untyped-decorator]
async def get_snippet_item(
    snippet_id: str,
    storage: Any = None,
) -> SnippetResponse:
    storage = get_storage()
    try:
        snippet = get_snippet(storage, snippet_id)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return SnippetResponse(
        id=snippet.id,
        title=snippet.metadata.title,
        content=snippet.content,
        description=snippet.metadata.description,
        language=snippet.metadata.language.value,
        tags=snippet.tags,
        created_at=snippet.created_at.isoformat(),
        updated_at=snippet.updated_at.isoformat(),
        metadata=snippet.metadata.model_dump()
        if hasattr(snippet.metadata, "model_dump")
        else snippet.metadata.__dict__,
    )


@router.put("/snippets/{snippet_id}", response_model=SnippetResponse)  # type: ignore[untyped-decorator]
async def update_snippet_item(
    snippet_id: str,
    body: SnippetCreateRequest,
    storage: Any = None,
) -> SnippetResponse:
    storage = get_storage()
    snippet = edit_snippet(
        storage,
        snippet_id,
        content=body.content,
        title=body.title,
        description=body.description or "",
        add_tags=body.tags or [],
    )
    return SnippetResponse(
        id=snippet.id,
        title=snippet.metadata.title,
        content=snippet.content,
        description=snippet.metadata.description,
        language=snippet.metadata.language.value,
        tags=snippet.tags,
        created_at=snippet.created_at.isoformat(),
        updated_at=snippet.updated_at.isoformat(),
        metadata=snippet.metadata.model_dump()
        if hasattr(snippet.metadata, "model_dump")
        else snippet.metadata.__dict__,
    )


@router.delete("/snippets/{snippet_id}")  # type: ignore[untyped-decorator]
async def delete_snippet_item(
    snippet_id: str,
    storage: Any = None,
) -> dict[str, str]:
    storage = get_storage()
    delete_snippet(storage, snippet_id)
    return {"status": "ok"}
