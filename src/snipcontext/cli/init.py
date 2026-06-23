"""Initialize a project-local SnipContext repository."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from snipcontext.config.paths import _PROJECT_DIR_NAME

console = Console()


def register_commands(app: typer.Typer) -> None:
    """Register init commands."""

    @app.command("init")  # type: ignore[untyped-decorator]
    def init(
        local: bool = typer.Option(False, "--local", help="Initialize project-local .snipcontext/"),
        path: str = typer.Option(".snipcontext", "--path", help="Target directory name"),
    ) -> None:
        """Scaffold a project-local .snipcontext/ directory."""
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

        console.print(f"[green]Initialized {target}[/green]")
        console.print("Project-local mode is now active in this directory.")
