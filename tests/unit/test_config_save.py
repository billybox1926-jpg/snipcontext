"""Unit tests for Config.save_to_file() error handling."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from typer import BadParameter

from snipcontext.config.settings import Config, reset_config


@pytest.fixture(autouse=True)
def _reset():
    reset_config()
    yield
    reset_config()


def _make_config(tmp_path: Path) -> Config:
    return Config()


def test_save_to_file_permission_error(tmp_path: Path):
    target = tmp_path / "config.yaml"
    config = _make_config(tmp_path)
    with patch("snipcontext.config.settings.get_config_path", return_value=target):
        with patch("builtins.open", side_effect=PermissionError("Access denied")):
            with pytest.raises(BadParameter) as excinfo:
                config.save_to_file()
            assert "Permission denied" in str(excinfo.value)


def test_save_to_file_file_exists_error(tmp_path: Path):
    target = tmp_path / "config.yaml"
    config = _make_config(tmp_path)
    with patch("snipcontext.config.settings.get_config_path", return_value=target):
        with patch("builtins.open", side_effect=FileExistsError("Config file already exists")):
            with pytest.raises(BadParameter) as excinfo:
                config.save_to_file()
            assert "already exists" in str(excinfo.value)


def test_save_to_file_os_error(tmp_path: Path):
    target = tmp_path / "config.yaml"
    config = _make_config(tmp_path)
    with patch("snipcontext.config.settings.get_config_path", return_value=target):
        with patch("builtins.open", side_effect=OSError("Disk full")):
            with pytest.raises(BadParameter) as excinfo:
                config.save_to_file()
            assert "OS error" in str(excinfo.value)
