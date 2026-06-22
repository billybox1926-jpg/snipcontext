# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for SnipContext standalone binary.

Build:
    pip install pyinstaller
    pyinstaller snipcontext.spec

Output:
    dist/snipcontext (or dist/snipcontext.exe on Windows)
"""

import sys
from pathlib import Path

block_cipher = None

# Project root
ROOT = Path(SPECPATH)

a = Analysis(
    [str(ROOT / "src" / "snipcontext" / "__main__.py")],
    pathex=[str(ROOT / "src")],
    binaries=[
        (str(ROOT / "scripts" / "snipcontext.cmd"), "."),
    ],
    datas=[
        (str(ROOT / "src" / "snipcontext"), "snipcontext"),
    ],
    hiddenimports=[
        "snipcontext.cli.app",
        "snipcontext.cli.main",
        "snipcontext.cli.config",
        "snipcontext.cli.context",
        "snipcontext.cli.snippets",
        "snipcontext.cli.search",
        "snipcontext.cli.export",
        "snipcontext.cli.watch",
        "snipcontext.cli.stats",
        "snipcontext.cli.crypto",
        "snipcontext.core.models",
        "snipcontext.core.storage",
        "snipcontext.core.search",
        "snipcontext.core.search_ops",
        "snipcontext.core.snippet_ops",
        "snipcontext.core.auto_tag",
        "snipcontext.core.config_ops",
        "snipcontext.core.crypto_ops",
        "snipcontext.core.sanitization",
        "snipcontext.core.watcher",
        "snipcontext.core.watch_ops",
        "snipcontext.config.settings",
        "snipcontext.plugins.base",
        "snipcontext.providers.base",
        "snipcontext.providers.claude",
        "snipcontext.providers.cursor",
        "snipcontext.providers.openai",
        "snipcontext.providers.generic",
        "yaml",
        "platformdirs",
        "rich",
        "typer",
        "pydantic",
        "pydantic_settings",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "matplotlib",
        "tkinter",
        "PyQt5",
        "PyQt6",
        "PySide2",
        "PySide6",
        "IPython",
        "jupyter",
        "notebook",
        "pytest",
        "ruff",
        "mypy",
        "mkdocs",
        "pre_commit",
        # Minimal-build exclusions (harmless for full build)
        "sentence_transformers",
        "faiss",
        "cryptography",
        "fastapi",
        "uvicorn",
        "prompt_toolkit",
    ],
    noarchive=False,
    optimize=0,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="snipcontext",
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # Append the .cmd wrapper on Windows so it lands next to the .exe
)
