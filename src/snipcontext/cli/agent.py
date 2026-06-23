"""Agent card CLI commands."""

from __future__ import annotations

import json
import logging

import typer
from rich.console import Console

from snipcontext.web.agent_card import build_agent_card

logger = logging.getLogger(__name__)
console = Console(width=0)


def register_commands(app: typer.Typer) -> None:
    """Register agent commands."""

    @app.command("agent-card")  # type: ignore[untyped-decorator]
    def agent_card() -> None:
        """Print the A2A agent card to stdout."""
        card = build_agent_card()
        print(json.dumps(card.model_dump(exclude_none=True), indent=2))
