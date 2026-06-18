#!/usr/bin/env python3
"""Setup script for SnipContext development environment.

Run this to install all dependencies and set up the project for development.
"""

import subprocess
import sys
from pathlib import Path


def run(cmd, **kwargs):
    """Run a shell command."""
    print(f"$ {cmd}")
    result = subprocess.run(cmd, shell=True, **kwargs)
    if result.returncode != 0:
        print(f"Command failed: {cmd}")
        sys.exit(1)
    return result


def main():
    project_root = Path(__file__).parent.parent

    print("=" * 60)
    print("SnipContext Development Setup")
    print("=" * 60)

    # Check Python version
    py_version = sys.version_info
    if py_version < (3, 9):
        print(f"Python 3.9+ required, found {py_version.major}.{py_version.minor}")
        sys.exit(1)
    print(f"Python {py_version.major}.{py_version.minor}.{py_version.micro} OK")

    # Install in editable mode with dev dependencies
    print("\n[1/4] Installing package in development mode...")
    run(f"{sys.executable} -m pip install -e \"{project_root}[dev]\"", cwd=project_root)

    # Verify key dependencies
    print("\n[2/4] Verifying dependencies...")
    try:
        import pydantic
        print(f"  pydantic {pydantic.__version__} OK")
    except ImportError:
        print("  WARNING: pydantic not found")

    try:
        import typer
        print(f"  typer {typer.__version__} OK")
    except ImportError:
        print("  WARNING: typer not found")

    try:
        import rich
        print(f"  rich OK")
    except ImportError:
        print("  WARNING: rich not found")

    try:
        import sentence_transformers
        print(f"  sentence-transformers OK")
    except ImportError:
        print("  WARNING: sentence-transformers not found (needed for semantic search)")

    try:
        import faiss
        print(f"  faiss OK")
    except ImportError:
        print("  WARNING: faiss not found (needed for semantic search)")

    # Create directories
    print("\n[3/4] Initializing SnipContext directories...")
    from platformdirs import user_data_dir

    data_dir = Path(user_data_dir("SnipContext", "snipcontext"))
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "snippets").mkdir(exist_ok=True)
    (data_dir / "index").mkdir(exist_ok=True)
    print(f"  Data directory: {data_dir}")

    # Run quick tests
    print("\n[4/4] Running quick validation tests...")
    result = run(f"{sys.executable} -m pytest {project_root / 'tests'} -x -q", cwd=project_root)

    print("\n" + "=" * 60)
    print("Setup complete! Try these commands:")
    print("  sc add 'print(\"hello\")' --title 'Hello' --tag python")
    print("  sc search 'hello world'")
    print("  sc list")
    print("  sc stats")
    print("=" * 60)


if __name__ == "__main__":
    main()
