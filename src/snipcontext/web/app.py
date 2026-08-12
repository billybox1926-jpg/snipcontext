"""FastAPI application factory."""

from __future__ import annotations

from pathlib import Path

from typing import Union

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from snipcontext.web.routers import agent, health, snippets, web_ui


def _web_dist_dir() -> Path | None:
    base_dir = Path(__file__).resolve().parent.parent.parent
    candidates = [
        base_dir / "web-ui" / "dist",
        base_dir / "src" / "snipcontext" / "web" / "static",
    ]
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    return None


def create_app() -> FastAPI:
    app = FastAPI(
        title="SnipContext API",
        summary="Programmatic access to your snippet collection.",
        version="0.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "vscode-webview://*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(snippets.router)
    app.include_router(agent.router)
    app.include_router(web_ui.router)

    @app.get("/", include_in_schema=False)  # type: ignore[untyped-decorator]
    async def root() -> JSONResponse:
        return JSONResponse({"status": "ok", "docs": "/docs"})

    dist_dir = _web_dist_dir()
    if dist_dir is not None:
        assets_dir = dist_dir / "assets"
        if assets_dir.is_dir():
            app.mount("/assets", StaticFiles(directory=assets_dir), name="web-assets")

        @app.get("/{full_path:path}", include_in_schema=False)  # type: ignore[untyped-decorator]
        async def serve_frontend(request_path: str) -> Union[JSONResponse, Response]:
            if request_path.startswith("api/") or request_path.startswith("docs/") or request_path.startswith("redoc"):
                return JSONResponse({"detail": "not found"}, status_code=404)
            candidate = dist_dir / request_path
            if request_path and candidate.is_file():
                return Response(candidate.read_bytes(), media_type="application/octet-stream")
            return JSONResponse((dist_dir / "index.html").read_bytes(), media_type="text/html")

    return app
