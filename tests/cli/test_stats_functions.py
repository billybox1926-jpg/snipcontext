"""Test stats.py internal functions directly."""
import pytest
from snipcontext.cli.stats import _format_size, _render_ascii_bar


def test_format_size_bytes():
    """_format_size formats bytes correctly."""
    assert "B" in _format_size(100)


def test_format_size_kilobytes():
    """_format_size formats KB correctly."""
    result = _format_size(1500)
    assert "KB" in result


def test_format_size_megabytes():
    """_format_size formats MB correctly."""
    result = _format_size(2 * 1024 * 1024)
    assert "MB" in result


def test_render_ascii_bar_empty():
    """_render_ascii_bar handles empty data."""
    result = _render_ascii_bar({})
    assert result == ["  (no data)"]


def test_render_ascii_bar_with_data():
    """_render_ascii_bar creates bar chart."""
    data = {"python": 5, "javascript": 3}
    result = _render_ascii_bar(data, max_width=20)
    assert len(result) == 2
