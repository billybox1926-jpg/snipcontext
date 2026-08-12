"""Web UI API routes.

Extends the existing SnipContext web API with endpoints needed by the
dashboard, search/browse UI, tag management, export integration, and
index management.
"""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import (
    APIRouter,
    Body,
    Depends,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
)

from snipcontext.config.settings import get_config
from snipcontext.core.models import Snippet
from snipcontext.core.search import HybridSearch
from snipcontext.core.search_ops import (
    export_snippets as core_export_snippets,
)
from snipcontext.core.search_ops import (
    search_snippets as core_search_snippets,
)
from snipcontext.core.storage import StorageEngine
from snipcontext.web.dependencies import get_storage
from snipcontext.web.schemas import ExportRequest
from snipcontext.web.websocket import manager

router = APIRouter(tags=["web-ui"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _snippet_to_list_item(snippet: Snippet) -> dict[str, Any]:
    return {
        "id": getattr(snippet, "id", ""),
        "title": getattr(snippet.metadata, "title", "") or "",
        "language": (
            getattr(snippet.metadata.language, "value", "")
            if getattr(snippet.metadata, "language", None)
            else ""
        ),
        "tags": list(getattr(snippet.metadata, "tags", []) or []),
        "updated_at": getattr(snippet.metadata, "updated_at", ""),
        "created_at": getattr(snippet, "created_at", ""),
    }


def _get_search(storage: StorageEngine = Depends(get_storage)) -> HybridSearch:
    return HybridSearch(get_config())


# ---------------------------------------------------------------------------
# Snippets list/detail/update/delete
# ---------------------------------------------------------------------------


@router.get("/snippets")
async def list_snippets(
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    language: str | None = Query(None),
    tag: str | None = Query(None),
    storage: StorageEngine = Depends(get_storage),
) -> dict[str, Any]:
    snippets = storage.list_all()
    if language:
        snippets = [
            s
            for s in snippets
            if (getattr(s.metadata, "language", None) or "").lower() == language.lower()
        ]
    if tag:
        snippets = [s for s in snippets if tag in (getattr(s.metadata, "tags", []) or [])]
    snippets.sort(key=lambda s: getattr(s.metadata, "updated_at", ""), reverse=True)
    total = len(snippets)
    page = snippets[offset : offset + limit]
    return {
        "items": [_snippet_to_list_item(s) for s in page],
        "total": total,
        "offset": offset,
        "limit": limit,
    }


@router.get("/snippets/{snippet_id}")
async def get_snippet(
    snippet_id: str, storage: StorageEngine = Depends(get_storage)
) -> dict[str, Any]:
    try:
        snippet = storage.get(snippet_id)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {
        "id": snippet.id,
        "title": getattr(snippet.metadata, "title", "") or "",
        "content": getattr(snippet, "content", "") or "",
        "language": (
            getattr(snippet.metadata.language, "value", "")
            if getattr(snippet.metadata, "language", None)
            else ""
        ),
        "tags": list(getattr(snippet.metadata, "tags", []) or []),
        "description": getattr(snippet.metadata, "description", ""),
        "created_at": getattr(snippet, "created_at", ""),
        "updated_at": getattr(snippet.metadata, "updated_at", ""),
        "deleted": bool(getattr(snippet, "deleted", False)),
        "metadata": (
            snippet.metadata.model_dump()
            if hasattr(snippet.metadata, "model_dump")
            else getattr(snippet.metadata, "__dict__", {})
        ),
    }


@router.put("/snippets/{snippet_id}")
async def update_snippet(
    snippet_id: str,
    body: dict[str, Any] = Body(...),
    storage: StorageEngine = Depends(get_storage),
) -> dict[str, Any]:
    try:
        snippet = storage.get(snippet_id)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    title = body.get("title")
    content = body.get("content")
    language = body.get("language")
    tags = body.get("tags")
    if title is not None:
        snippet.metadata.title = title
    if content is not None:
        snippet.content = content
    if language is not None:
        try:
            snippet.metadata.language = language
        except Exception:
            pass
    if tags is not None:
        snippet.metadata.tags = list(tags)

    storage.save(snippet)
    await manager.broadcast({"type": "snippet_updated", "id": snippet_id})
    return await get_snippet(snippet_id, storage)


@router.delete("/snippets/{snippet_id}")
async def delete_snippet(
    snippet_id: str, storage: StorageEngine = Depends(get_storage)
) -> dict[str, bool]:
    try:
        storage.mark_deleted(snippet_id)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await manager.broadcast({"type": "snippet_deleted", "id": snippet_id})
    return {"ok": True}


# ---------------------------------------------------------------------------
# Tags
# ---------------------------------------------------------------------------


@router.get("/tags")
async def list_tags(storage: StorageEngine = Depends(get_storage)) -> dict[str, Any]:
    snippets = storage.list_all()
    counts: dict[str, int] = {}
    for s in snippets:
        for t in getattr(s.metadata, "tags", []) or []:
            counts[t] = counts.get(t, 0) + 1
    tags = [{"name": name, "count": count} for name, count in sorted(counts.items())]
    return {"items": tags, "total": len(tags)}


@router.put("/tags/{tag_name}")
async def rename_tag(
    tag_name: str,
    body: dict[str, Any] = Body(...),
    storage: StorageEngine = Depends(get_storage),
) -> dict[str, Any]:
    new_name = str(body.get("new_name") or "").strip()
    if not new_name:
        raise HTTPException(status_code=400, detail="new_name is required")
    snippets = storage.list_all()
    changed = 0
    for s in snippets:
        tags = list(getattr(s.metadata, "tags", []) or [])
        if tag_name in tags:
            s.metadata.tags = [new_name if t == tag_name else t for t in tags]
            storage.save(s)
            changed += 1
    await manager.broadcast({"type": "tags_updated"})
    return {"ok": True, "updated": changed}


@router.delete("/tags/{tag_name}")
async def delete_tag(
    tag_name: str, storage: StorageEngine = Depends(get_storage)
) -> dict[str, Any]:
    snippets = storage.list_all()
    changed = 0
    for s in snippets:
        tags = list(getattr(s.metadata, "tags", []) or [])
        if tag_name in tags:
            s.metadata.tags = [t for t in tags if t != tag_name]
            storage.save(s)
            changed += 1
    await manager.broadcast({"type": "tags_updated"})
    return {"ok": True, "updated": changed}


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------


@router.get("/search")
async def search_items(
    q: str = Query(..., min_length=1),
    mode: str = Query("hybrid", pattern="^(semantic|keyword|hybrid)$"),
    top_k: int = Query(10, ge=1, le=50),
    storage: StorageEngine = Depends(get_storage),
    search: HybridSearch = Depends(_get_search),
) -> dict[str, Any]:
    results = core_search_snippets(storage, search, query=q, mode=mode, top_k=top_k)
    items = []
    for item in results:
        snippet = getattr(item, "snippet", None)
        if isinstance(snippet, Snippet):
            entry = _snippet_to_list_item(snippet)
            entry["score"] = float(getattr(item, "score", 0.0) or 0.0)
            items.append(entry)
    return {"items": items, "total": len(items), "query": q, "mode": mode}


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------


@router.post("/export")
async def export_items(
    body: dict[str, Any] = Body(...),
    storage: StorageEngine = Depends(get_storage),
    search: HybridSearch = Depends(_get_search),
) -> dict[str, Any]:
    try:
        request = ExportRequest(**body)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    snippets, formatted = core_export_snippets(
        storage=storage,
        search=search,
        provider_name=request.provider,
        ids=request.ids,
        query=request.query,
        top_k=request.top_k,
    )
    return {
        "format": request.provider,
        "content": formatted,
        "snippet_count": len(snippets),
    }


# ---------------------------------------------------------------------------
# Index status/rebuild
# ---------------------------------------------------------------------------


@router.get("/index/status")
async def index_status(
    search: HybridSearch = Depends(_get_search),
    storage: StorageEngine = Depends(get_storage),
) -> dict[str, Any]:
    vector_index = getattr(search, "vector_index", None)
    backend_name = getattr(vector_index, "backend_name", lambda: "unknown")()
    vector_count = 0
    if vector_index is not None:
        index_obj = getattr(vector_index, "index", None)
        if index_obj is not None:
            vector_count = int(getattr(index_obj, "ntotal", 0) or 0)
    last_rebuild = getattr(search, "last_rebuild", None)
    snippets = storage.list_all()
    return {
        "index_type": backend_name,
        "vector_count": vector_count,
        "last_rebuild": last_rebuild.isoformat() if last_rebuild else None,
        "snippet_count": len(snippets),
    }


@router.post("/index/rebuild")
async def rebuild_index(
    search: HybridSearch = Depends(_get_search),
    storage: StorageEngine = Depends(get_storage),
) -> dict[str, bool]:
    await manager.broadcast({"type": "index_rebuild_started"})
    asyncio.create_task(_rebuild_and_notify(search, storage))
    return {"ok": True}


async def _rebuild_and_notify(search: HybridSearch, storage: StorageEngine) -> None:
    try:
        snippets = storage.list_all()
        await asyncio.get_event_loop().run_in_executor(None, search.rebuild_incremental, snippets)
        await manager.broadcast({"type": "index_rebuild_completed"})
    except Exception as exc:  # pragma: no cover - background path
        await manager.broadcast({"type": "index_rebuild_failed", "error": str(exc)})


# ---------------------------------------------------------------------------
# WebSocket
# ---------------------------------------------------------------------------


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
