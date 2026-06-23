"""A2A Agent Card builder."""

from __future__ import annotations

from snipcontext import __version__
from snipcontext.web.schemas import AgentCard, AgentSkill


def build_agent_card(base_url: str | None = None) -> AgentCard:
    """Build the A2A Agent Card from application metadata."""
    return AgentCard(
        name="SnipContext",
        description="Semantic snippet manager — search, store, and export code snippets",
        version=__version__,
        skills=[
            AgentSkill(
                id="search",
                name="Search snippets",
                description="Semantic + keyword search across snippets",
                input_modes=["text/plain"],
                output_modes=["application/json"],
            ),
            AgentSkill(
                id="store",
                name="Store snippet",
                description="Add a new snippet to the collection",
                input_modes=["application/json"],
                output_modes=["application/json"],
            ),
            AgentSkill(
                id="export",
                name="Export snippets",
                description="Export snippets in provider format",
                input_modes=["text/plain"],
                output_modes=["text/plain"],
            ),
            AgentSkill(
                id="stats",
                name="Get statistics",
                description="Retrieve collection statistics",
                input_modes=["text/plain"],
                output_modes=["application/json"],
            ),
        ],
        authentication={"type": "none"},
        endpoint=base_url,
    )
