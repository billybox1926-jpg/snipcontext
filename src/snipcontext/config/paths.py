"""Path resolution and discovery for SnipContext storage."""

from __future__ import annotations

import os
from pathlib import Path

from platformdirs import user_config_dir, user_data_dir

_APP_NAME = "SnipContext"
_APP_AUTHOR = "snipcontext"
_PROJECT_DIR_NAME = ".snipcontext"


def find_project_root(start: Path | None = None) -> Path | None:
    """Walk up from start until a .snipcontext/ directory is found."""
    start = start or Path.cwd()
    for parent in [start, *start.parents]:
        if (parent / _PROJECT_DIR_NAME).is_dir():
            return parent
    return None


def is_project_local() -> bool:
    """Returns True if a .snipcontext/ directory was found in the filesystem."""
    return find_project_root() is not None


def get_storage_root() -> Path:
    """Return the effective storage root.

    Priority:
      1. SNIPCONTEXT_HOME env var (if set)
      2. .snipcontext/ in CWD or nearest parent (project-local)
      3. platformdirs user_data_dir (global fallback)
    """
    env_home = os.environ.get("SNIPCONTEXT_HOME")
    if env_home:
        return Path(env_home).expanduser().resolve()

    project_root = find_project_root()
    if project_root:
        return (project_root / _PROJECT_DIR_NAME).resolve()

    return Path(user_data_dir(_APP_NAME, _APP_AUTHOR))


def get_config_path() -> Path:
    """Return the effective config file path.

    Project-local takes precedence over global when .snipcontext/ exists.
    """
    project_root = find_project_root()
    if project_root:
        return (project_root / _PROJECT_DIR_NAME / "config.yaml").resolve()

    return Path(user_config_dir(_APP_NAME, _APP_AUTHOR)) / "snipcontext.yaml"
