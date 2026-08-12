"""FastAPI application factory."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from snipcontext.web.routers import agent, health, snippets, web_ui


def _web_dist_dir() -> Path | None:
    # app.py is at src/snipcontext/web/app.py. Walk up 3 levels to reach the
    # repo root (web/ → snipcontext/ → src/ → repo-root), then look for web-ui/dist.
    # On case-insensitive filesystems (Windows), Path().resolve() may uppercase
    # the first dir letter ("Snipcontext"), so also probe case-insensitively.
    file_dir = Path(__file__).resolve().parent  # .../web/
    repo_root = file_dir.parent.parent.parent  # .../repo-root/  (3 parents)
    primary = repo_root / "web-ui" / "dist"
    if primary.is_dir():
        return primary
    # Case-insensitive fallback: find a sibling named "web-ui" (any case)
    for sibling in repo_root.iterdir():
        if sibling.is_dir() and sibling.name.lower() == "web-ui":
            candidate = sibling / "dist"
            if candidate.is_dir():
                return candidate
    # Last resort: bundled static dir next to this file
    static = file_dir / "static"
    if static.is_dir():
        return static
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

    dist_dir = _web_dist_dir()
    if dist_dir is not None:
        assets_dir = dist_dir / "assets"
        if assets_dir.is_dir():
            app.mount("/assets", StaticFiles(directory=assets_dir), name="web-assets")

        @app.get("/index.html", include_in_schema=False)  # type: ignore[untyped-decorator]
        async def index_html() -> Response:
            return Response((dist_dir / "index.html").read_bytes(), media_type="text/html")

        @app.get("/{request_path:path}", include_in_schema=False, response_model=None)  # type: ignore[untyped-decorator]
        async def serve_frontend(request_path: str) -> Response:
            if (
                request_path.startswith("api/")
                or request_path.startswith("docs/")
                or request_path.startswith("redoc")
            ):
                return JSONResponse({"detail": "not found"}, status_code=404)
            candidate = dist_dir / request_path
            if request_path and candidate.is_file():
                return Response(candidate.read_bytes(), media_type="application/octet-stream")
            return Response((dist_dir / "index.html").read_bytes(), media_type="text/html")

    return app
