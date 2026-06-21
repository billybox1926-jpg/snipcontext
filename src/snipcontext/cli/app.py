"""SnipContext CLI application entry point.

Creates the root Typer app and registers all domain sub-commands.
"""

from __future__ import annotations

import logging
import sys

import typer
from rich.console import Console
from rich.logging import RichHandler

from snipcontext.cli.context import reset_context

# Configure logging with Rich
logging.basicConfig(
    level=logging.WARNING,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)],
)
logger = logging.getLogger(__name__)

# Root Typer app
app = typer.Typer(
    name="snipcontext",
    help="SnipContext — AI-powered code snippet & context manager",
    rich_markup_mode="rich",
    no_args_is_help=True,
    add_completion=True,
)

# Config sub-command group
config_app = typer.Typer(name="config", help="Manage configuration")
app.add_typer(config_app)


@app.callback()  # type: ignore[untyped-decorator]
def main(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output"),
    debug: bool = typer.Option(False, "--debug", help="Enable debug logging"),
    reload: bool = typer.Option(False, "--reload", help="Force reload of config and search index"),
) -> None:
    """SnipContext — save, search, and export your best code for LLMs."""
    if debug:
        logging.getLogger().setLevel(logging.DEBUG)
    elif verbose:
        logging.getLogger().setLevel(logging.INFO)
    if reload:
        reset_context()
        logger.debug("Shared context reset via --reload flag")


# ── Register domain commands ───────────────────────────────────────────
# Each domain module provides a register_commands(app) function.

from snipcontext.cli.config import register_commands as register_config  # noqa: E402
from snipcontext.cli.export import register_commands as register_export  # noqa: E402
from snipcontext.cli.search import register_commands as register_search  # noqa: E402
from snipcontext.cli.snippets import register_commands as register_snippets  # noqa: E402
from snipcontext.cli.stats import register_commands as register_stats  # noqa: E402
from snipcontext.cli.watch import register_commands as register_watch  # noqa: E402

register_snippets(app)
register_search(app)
register_export(app)
register_watch(app)
register_stats(app)
register_config(config_app)

# Optional: cryptography commands (requires snipcontext[encryption])
try:
    from snipcontext.cli.crypto import register_commands as register_crypto  # noqa: E402
    register_crypto(app)
except ImportError:
    pass  # cryptography not installed, skip encrypt/decrypt commands


@app.command()
def repl(
    script: str | None = typer.Option(None, "--script", help="Run a TUI script file and exit"),
) -> None:
    """Start the interactive SnipContext shell."""
    try:
        from snipcontext.tui.app import run
    except ImportError as exc:
        console = Console()
        console.print("[red]The interactive shell requires the optional 'tui' extra.[/red]")
        console.print("Install it with: pip install snipcontext[tui]")
        raise typer.Exit(1) from exc
    sys.exit(run())


if __name__ == "__main__":
    app()
