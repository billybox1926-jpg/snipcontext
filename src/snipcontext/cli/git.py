"""Git domain CLI commands for SnipContext.

Provides `sc git status`, `sc git pull`, and `sc git push`, matching
the conventions established by `sc init --git` and the existing CLI
error/output style (Rich markup, non-zero exit on failure).
"""

from __future__ import annotations

import sys

import typer
from rich.console import Console

from snipcontext.cli.context import get_context as _get_context
from snipcontext.core.git_integration import GitError, GitIntegration

console = Console()

git_app = typer.Typer(
    name="git",
    help="Git-backed sync for snippet collections",
    no_args_is_help=True,
)


@git_app.command("status")
def git_status() -> None:
    """Show git status for the current snippet collection."""
    config, storage, _ = _get_context()
    gi = GitIntegration(config.storage.data_dir)

    if not gi.is_initialized():
        console.print("[yellow]Not a git repository. Run `sc init --local --git` first.[/yellow]")
        raise typer.Exit(1)

    try:
        output = gi.status()
    except GitError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1)

    console.print(output)


@git_app.command("pull")
def git_pull(
    force: bool = typer.Option(False, "--force", help="Skip conflict check and pull anyway."),
) -> None:
    """Pull latest snippet collection from the remote.

    Runs conflict detection first and blocks if the same snippet was
    edited on both sides since the last common ancestor.
    """
    config, storage, _ = _get_context()
    gi = GitIntegration(config.storage.data_dir)

    if not gi.is_initialized():
        console.print("[yellow]Not a git repository. Run `sc init --local --git` first.[/yellow]")
        raise typer.Exit(1)

    if not force:
        try:
            report = gi.detect_conflicts(storage)
        except GitError as exc:
            console.print(f"[red]{exc}[/red]")
            raise typer.Exit(1)

        if report.has_conflicts:
            if not sys.stdin.isatty():
                console.print(f"[yellow]{report.summary()}[/yellow]")
                console.print(
                    "Run with --force to pull anyway, or resolve manually first "
                    "(consider `git stash` if you have uncommitted local edits)."
                )
                # 2 = blocked by conflict detection; caller should inspect/manually resolve.
                raise typer.Exit(code=2)

            # Interactive resolution
            for c in report.conflicts:
                console.print(f"\n[yellow]Conflict in snippet {c.snippet_id}[/yellow]")
                try:
                    diff = gi.get_conflict_diff(c.snippet_id, storage)
                    if diff:
                        console.print(diff)
                except GitError as exc:
                    console.print(f"[red]Could not show diff: {exc}[/red]")

                choice = typer.prompt(
                    "Choose: [l]ocal, [r]emote, [s]tash-and-pull, [a]bort", default="a"
                ).strip().lower()

                if choice == "l":
                    gi.resolve_accept_local(c.snippet_id, storage)
                    console.print(f"  → Keeping local version of {c.snippet_id}")
                elif choice == "r":
                    gi.resolve_accept_remote(c.snippet_id, storage)
                    console.print(f"  → Accepting remote version of {c.snippet_id}")
                elif choice == "s":
                    console.print("  → Stashing local changes, pulling, then restoring...")
                    gi.stash()
                    console.print(gi.pull())
                    gi.stash_pop()
                    console.print("[green]Pull complete with stash restored.[/green]")
                    raise typer.Exit(code=0)
                else:
                    console.print("Aborted.")
                    raise typer.Exit(code=2)

    try:
        console.print(gi.pull())
    except GitError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1)


@git_app.command("push")
def git_push() -> None:
    """Push local snippet collection to the remote."""
    config, storage, _ = _get_context()
    gi = GitIntegration(config.storage.data_dir)

    if not gi.is_initialized():
        console.print("[yellow]Not a git repository. Run `sc init --local --git` first.[/yellow]")
        raise typer.Exit(1)

    try:
        console.print(gi.push())
    except GitError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1)


def register_commands(app: typer.Typer) -> None:
    """Register git subcommands on the root Typer app."""
    app.add_typer(git_app, name="git", help="Git-backed sync for snippet collections")
