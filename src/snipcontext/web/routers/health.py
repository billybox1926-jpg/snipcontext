"""Minimal health router."""

from fastapi import APIRouter

from snipcontext.web.schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)  # type: ignore[untyped-decorator]
async def health() -> HealthResponse:
    return HealthResponse(status="ok")
