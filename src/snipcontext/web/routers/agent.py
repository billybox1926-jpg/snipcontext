"""A2A Agent Card router."""

from __future__ import annotations

from fastapi import APIRouter, Request

from snipcontext.web.agent_card import build_agent_card

router = APIRouter(tags=["a2a"])


@router.get("/.well-known/agent.json")
async def get_agent_card(request: Request) -> dict[str, object]:
    """A2A Agent Card endpoint."""
    base_url = str(request.base_url).rstrip("/")
    card = build_agent_card(base_url)
    return card.model_dump(exclude_none=True)
