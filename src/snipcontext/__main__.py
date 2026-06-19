"""SnipContext runtime CLI facade.

Prefers the full Typer CLI when available; otherwise falls back to a minimal
stdlib-only no-op entry point so `python -m snipcontext` is always executable.
"""

from __future__ import annotations


def get_app():
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

        @app.command()
        def demo():
            """Run the SnipContext demo."""
            print("SnipContext demo not available in minimal runtime.")

        return app


if __name__ == "__main__":
    get_app()()
