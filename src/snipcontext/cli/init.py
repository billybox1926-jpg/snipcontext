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
        local: str | None = typer.Option(
            None, "--local", help="Path to initialize (defaults to CWD if omitted)"
        ),
        force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing config"),
        template: str | None = typer.Option(
            None, "--template", help="Path to a JSON snippet template to copy"
        ),
        git: bool = typer.Option(False, "--git", help="Initialize git repo in target directory"),
        remote: str | None = typer.Option(None, "--remote", help="Git remote URL"),
    ) -> None:
        """Scaffold a project-local .snipcontext/ directory with optional Git setup."""
        # Use provided local path, or fallback to current working directory
        root_dir = Path(local).resolve() if local else Path.cwd()
        target = root_dir / ".snipcontext"

        if target.exists() and not force:
            console.print(f"[red]Error: {target} already exists[/red]")
            console.print("Use --force to overwrite the configuration.")
            raise typer.Exit(1)

        target.mkdir(parents=True, exist_ok=True)
        snippets_dir = target / "snippets"
        snippets_dir.mkdir(exist_ok=True)
        (target / ".gitignore").write_text("index.faiss\n", encoding="utf-8")

        import json

        from snipcontext.config.settings import Config

        # Generate defaults using Config model
        config = Config()
        config.storage.data_dir = target.resolve()
        payload = config.model_dump(mode="json", exclude_none=True)

        # Write default config.json
        (target / "config.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

        if template:
            template_path = Path(template)
            if template_path.exists() and template_path.is_file():
                dest = snippets_dir / template_path.name
                shutil.copy2(template_path, dest)
                console.print(f"[green]Copied template {template_path.name} to {dest}[/green]")
            else:
                console.print(
                    f"[yellow]Warning: Template {template} not found or is not a file.[/yellow]"
                )

        if git:
            _init_git(target, remote)

        console.print(f"[green]Initialized {target}[/green]")
        console.print("Project-local mode is now active in this directory.")
