"""FastAPI application factory."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from snipcontext.web.routers import agent, health, snippets


def create_app() -> FastAPI:
    app = FastAPI(
        title="SnipContext API",
        summary="Programmatic access to your snippet collection.",
        version="0.1.0",
    )

    app.include_router(health.router)
    app.include_router(snippets.router)
    app.include_router(agent.router)

    @app.get("/", include_in_schema=False)  # type: ignore[untyped-decorator]
    async def root() -> JSONResponse:
        return JSONResponse({"status": "ok", "docs": "/docs"})

    return app
