"""Rich output formatting for REPL results."""

from __future__ import annotations

from typing import Any

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

_console = Console()


def format_output(result: Any):
    if result is None:
        return None
    if isinstance(result, str):
        return Text(result)
    if isinstance(result, dict):
        rtype = result.get("type")
        if rtype == "snippet":
            return _snippet_panel(result["item"])
        if rtype == "snippet_list":
            return _snippet_table(result["items"])
        if rtype == "search_results":
            return _snippet_table([r.snippet for r in result["items"]])
        if rtype == "stats":
            return _stats_panel(result["data"])
        if rtype == "config":
            return _config_panel(result["data"])
        if rtype == "config_paths":
            return _config_paths_table(result["data"])
        if rtype == "export":
            return Text(result["output"])
        if rtype == "providers":
            return _providers_table(result["items"])
        if rtype == "message":
            return Text(result["message"])
        if rtype == "error":
            return Text(f"[red]{result['message']}[/red]")
    return Text(str(result))


def _snippet_panel(snippet) -> Panel:
    title = f"{snippet.metadata.title} [{snippet.id[:8]}]"
    content = Text()
    if snippet.metadata.description:
        content.append(f"{snippet.metadata.description}\n", "dim")
    content.append(f"Language: {snippet.metadata.language.value}\n", "green")
    if snippet.tags:
        content.append(f"Tags: {', '.join(snippet.tags)}\n", "yellow")
    text = snippet.content or ""
    try:
        syntax = Syntax(
            text,
            snippet.metadata.language.value
            if snippet.metadata.language.value != "unknown"
            else "text",
            theme="monokai",
            line_numbers=False,
            word_wrap=True,
        )
        return Panel(syntax, title=title, border_style="cyan", padding=(0, 1))
    except Exception:
        return Panel(Text(text), title=title, border_style="cyan", padding=(0, 1))


def _snippet_table(snippets) -> Table:
    from datetime import datetime

    table = Table(
        title=f"Snippets ({len(snippets)} total)",
        show_header=True,
        header_style="bold magenta",
        box=box.SIMPLE,
    )
    table.add_column("ID", style="dim", no_wrap=True, width=8)
    table.add_column("Title", style="cyan")
    table.add_column("Language", style="green", width=12)
    table.add_column("Tags", style="yellow", width=20)
    table.add_column("Updated", style="dim", width=10)
    for s in snippets:
        updated = s.updated_at.strftime("%Y-%m-%d") if isinstance(s.updated_at, datetime) else "?"
        table.add_row(
            s.id[:6],
            s.metadata.title,
            s.metadata.language.value,
            ", ".join(s.tags[:3]) + ("..." if len(s.tags) > 3 else ""),
            updated,
        )
    return table


def _stats_panel(data: dict) -> Panel:
    lines = [
        f"Snippets: {data.get('total_snippets', 0)}",
        f"Unique Tags: {data.get('total_tags', 0)}",
        f"Languages: {len(data.get('languages', {}))}",
        "",
        "By Language:",
    ]
    for lang, count in data.get("languages", {}).items():
        lines.append(f"  {lang}: {count}")
    return Panel("\n".join(lines), title="Stats", border_style="green")


def _config_panel(data: dict) -> Panel:
    import yaml

    return Panel(
        yaml.safe_dump(data, default_flow_style=False, sort_keys=False),
        title="Configuration",
        border_style="blue",
    )


def _config_paths_table(data: dict) -> Table:
    table = Table(title="Paths", show_header=True, box=box.SIMPLE)
    table.add_column("Key", style="cyan")
    table.add_column("Path", style="white")
    for k, v in data.items():
        table.add_row(k, str(v))
    return table


def _providers_table(providers: list[tuple[str, str, str]]) -> Table:
    table = Table(title="Export Providers", show_header=True, box=box.SIMPLE)
    table.add_column("Name", style="cyan")
    table.add_column("Description", style="white")
    table.add_column("Format", style="green")
    for name, desc, fmt in providers:
        table.add_row(name, desc, fmt)
    return table
