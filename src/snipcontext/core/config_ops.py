"""Config domain business logic.

Pure functions for configuration management.
No I/O, no CLI dependencies.
"""

from __future__ import annotations

from snipcontext.config.settings import Config


def get_config_paths(config: Config) -> dict[str, str]:
    """Return config and data directory paths.

    Args:
        config: The application config instance.

    Returns:
        Dict with 'config_file', 'data_dir', 'snippets', 'index' paths.
    """
    return {
        "config_file": str(config.config_file_path),
        "data_dir": str(config.storage.data_dir),
        "snippets": str(config.snippets_path),
        "index": str(config.index_path),
    }


def get_config_values(config: Config) -> dict:
    """Return serializable config values for display.

    Args:
        config: The application config instance.

    Returns:
        Dict of config values suitable for serialization.
    """
    return config.model_dump(mode="json")
