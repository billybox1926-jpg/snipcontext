"""SnipContext runtime CLI facade.

Prefers the full Typer CLI when available; otherwise falls back to a minimal
stdlib-only no-op entry point so `python -m snipcontext` is always executable.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import typer


def get_app() -> typer.Typer:
    try:
        from snipcontext.cli.main import app

        return app
    except Exception:
        try:
            import typer
        except Exception as exc:  # pragma: no cover - defensive fallback
            print(f"SnipContext CLI unavailable: {exc}")
            raise SystemExit(1) from exc

        app = typer.Typer(add_completion=True)

        @app.command()  # type: ignore[untyped-decorator]
        def demo() -> None:
            """Run the SnipContext demo."""
            print("SnipContext demo not available in minimal runtime.")

        return app


if __name__ == "__main__":
    get_app()()
