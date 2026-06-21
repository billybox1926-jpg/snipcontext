"""SnipContext TUI Application - Main REPL Loop.

Provides the interactive terminal-based interface for SnipContext.
"""

from __future__ import annotations

import sys
from pathlib import Path

from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.history import FileHistory
from prompt_toolkit.styles import Style
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from snipcontext.cli.context import get_context as _get_context
from snipcontext.tui.commands import CommandRegistry
from snipcontext.tui.completer import SnipContextCompleter
from snipcontext.tui.formatter import format_output


def _get_history_path() -> Path:
    from snipcontext.config.settings import get_config

    config = get_config()
    return config.storage.data_dir / "repl_history"


def _create_session() -> PromptSession:
    history_path = _get_history_path()
    history_path.parent.mkdir(parents=True, exist_ok=True)

    return PromptSession(
        history=FileHistory(str(history_path)),
        auto_suggest=AutoSuggestFromHistory(),
        style=Style.from_dict(
            {
                "prompt": "ansicyan bold",
                "completion-menu.completion": "bg:#008888 #ffffff",
                "completion-menu.completion.current": "bg:#00aaaa #000000",
                "scrollbar.background": "bg:#88aaaa",
                "scrollbar.button": "bg:#222222",
            }
        ),
    )


def _print_welcome() -> None:
    console = Console()
    welcome = Text.assemble(
        ("SnipContext ", "bold cyan"),
        ("Interactive Shell\n", "cyan"),
        ("Type ", "dim"),
        ("help", "bold"),
        (" for commands, ", "dim"),
        ("exit", "bold"),
        (" or ", "dim"),
        ("Ctrl+D", "bold"),
        (" to quit.\n", "dim"),
    )
    console.print(Panel(welcome, border_style="cyan", padding=(0, 1)))


def _print_help() -> None:
    registry = CommandRegistry()
    console = Console()
    help_text = Text()
    help_text.append("Available Commands:\n\n", "bold underline")

    for name, spec in sorted(registry.commands.items()):
        # skip aliases in help listing
        if name != spec.name:
            continue
        help_text.append(f"  {name}", "bold cyan")
        if spec.aliases:
            help_text.append(f" ({', '.join(spec.aliases)})", "dim cyan")
        help_text.append(f" - {spec.description}\n", "white")

    help_text.append("\n", "dim")
    help_text.append("Features:\n", "bold underline")
    help_text.append("  • Tab completion for commands, flags, and snippet IDs\n")
    help_text.append("  • Command history (up/down arrows)\n")
    help_text.append("  • Type ", "dim")
    help_text.append("help <command>", "bold")
    help_text.append(" for detailed usage hints\n")
    help_text.append("  • Type ", "dim")
    help_text.append("exit", "bold")
    help_text.append(" or press ", "dim")
    help_text.append("Ctrl+D", "bold")
    help_text.append(" to quit\n", "dim")

    console.print(Panel(help_text, title="Help", border_style="blue", padding=(1, 2)))


def run() -> int:
    _print_welcome()

    session = _create_session()
    console = Console()
    registry = CommandRegistry()
    completer = SnipContextCompleter(registry)

    try:
        _get_context()
    except Exception as exc:
        console.print(f"[red]Failed to initialize context: {exc}[/red]")
        return 1

    while True:
        try:
            prompt_text = Text.assemble(("snipcontext", "bold cyan"), (" > ", "cyan"))
            user_input = session.prompt(prompt_text, completer=completer)

            if not user_input.strip():
                continue

            cmd = user_input.strip().lower()
            if cmd in ("exit", "quit"):
                console.print("[dim]Goodbye![/dim]")
                return 0
            if cmd in ("help", "?"):
                _print_help()
                continue

            result = registry.execute(user_input)
            formatted = format_output(result)
            if formatted is not None:
                console.print(formatted)

        except KeyboardInterrupt:
            console.print("\n[dim]Use 'exit' or Ctrl+D to quit.[/dim]")
            continue
        except EOFError:
            console.print("\n[dim]Goodbye![/dim]")
            return 0

    return 0


if __name__ == "__main__":
    sys.exit(run())
