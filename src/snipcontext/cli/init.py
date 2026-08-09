"""Initialize a project-local SnipContext repository with optional Git setup."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import typer
from rich.console import Console

console = Console()


def _run_git(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
    )


def _init_git(target: Path, remote: str | None = None) -> None:
    if not shutil.which("git"):
        console.print("[red]Error: git is not installed or not on PATH[/red]")
        raise typer.Exit(1)

    init = _run_git(["init", "-b", "main"], target)
    if init.returncode != 0:
        console.print(f"[red]git init failed: {init.stderr.strip()}[/red]")
        raise typer.Exit(1)

    gitignore = target / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text(
            "\n".join(
                [
                    "index.faiss",
                    "keyword_index.json",
                    "keyword_index.pkl",
                    "*.tmp",
                    ".env",
                    ".snipcontext-env",
                    "search_history.db",
                    "*.db",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

    config_email = _run_git(["config", "user.email", "snipcontext@local"], target)
    if config_email.returncode != 0:
        console.print(
            f"[yellow]Warning: could not set git identity: {config_email.stderr.strip()}[/yellow]"
        )

    config_name = _run_git(["config", "user.name", "SnipContext"], target)
    if config_name.returncode != 0:
        console.print(
            f"[yellow]Warning: could not set git identity: {config_name.stderr.strip()}[/yellow]"
        )

    add = _run_git(["add", "."], target)
    if add.returncode != 0:
        console.print(f"[red]git add failed: {add.stderr.strip()}[/red]")
        raise typer.Exit(1)

    commit = _run_git(
        ["commit", "-m", "chore: initialize SnipContext storage"],
        target,
    )
    if commit.returncode not in (0, 1):
        console.print(f"[red]git commit failed: {commit.stdout.strip()}[/red]")
        raise typer.Exit(1)

    if remote:
        add_remote = _run_git(["remote", "add", "origin", remote], target)
        if add_remote.returncode != 0 and "already exists" not in add_remote.stderr:
            console.print(f"[red]git remote add failed: {add_remote.stderr.strip()}[/red]")
            raise typer.Exit(1)


def register_commands(app: typer.Typer) -> None:
    """Register init commands."""

    @app.command("init")  # type: ignore[untyped-decorator]
    def init(
        local: bool = typer.Option(False, "--local", help="Initialize project-local .snipcontext/"),
        path: str = typer.Option(".snipcontext", "--path", help="Target directory name"),
        git: bool = typer.Option(False, "--git", help="Initialize git repo in target directory"),
        remote: str | None = typer.Option(None, "--remote", help="Git remote URL"),
    ) -> None:
        """Scaffold a project-local .snipcontext/ directory with optional Git setup."""
        if not local:
            console.print("[yellow]Usage: sc init --local[/yellow]")
            raise typer.Exit(1)

        target = Path.cwd() / path
        if target.exists():
            console.print(f"[red]Error: {target} already exists[/red]")
            raise typer.Exit(1)

        target.mkdir(parents=True)
        (target / "snippets").mkdir()
        (target / ".gitignore").write_text("index.faiss\n")

        import yaml

        payload = {
            "storage": {
                "data_dir": str(target.resolve()),
                "snippets_dir": "snippets",
                "index_dir": "index",
            }
        }
        (target / "config.yaml").write_text(
            yaml.safe_dump(payload, default_flow_style=False, sort_keys=False)
        )

        if git:
            _init_git(target, remote)

        console.print(f"[green]Initialized {target}[/green]")
        console.print("Project-local mode is now active in this directory.")
