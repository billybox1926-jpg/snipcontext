"""Tests for core/auto_tag.py."""

from unittest.mock import MagicMock, patch

import pytest

from snipcontext.core.auto_tag import AutoTagService, SnippetNeighbor


def test_snippet_neighbor_creation():
    """SnippetNeighbor dataclass creates correctly."""
    neighbor = SnippetNeighbor(snippet_id="test-123", score=0.95)
    assert neighbor.snippet_id == "test-123"
    assert neighbor.score == 0.95


def test_auto_tag_service_initialization():
    """AutoTagService initializes with correct dependencies."""
    mock_index = MagicMock()
    mock_storage = MagicMock()
    mock_config = MagicMock()

    service = AutoTagService(
        vector_index=mock_index,
        storage=mock_storage,
        config=mock_config,
    )

    assert service.vector_index is mock_index
    assert service.storage is mock_storage
    assert service.config is mock_config


def test_suggest_returns_empty_when_not_trained():
    """suggest() returns empty list when index is not trained."""
    mock_index = MagicMock()
    mock_index.is_trained = False
    mock_storage = MagicMock()
    mock_config = MagicMock()

    service = AutoTagService(
        vector_index=mock_index,
        storage=mock_storage,
        config=mock_config,
    )

    result = service.suggest([0.1, 0.2, 0.3])
    assert result == []


def test_suggest_with_numpy_import_error():
    """suggest() raises RuntimeError when numpy is not available."""
    mock_index = MagicMock()
    mock_index.is_trained = True
    mock_storage = MagicMock()
    mock_config = MagicMock()

    service = AutoTagService(
        vector_index=mock_index,
        storage=mock_storage,
        config=mock_config,
    )

    with patch.dict("sys.modules", {"numpy": None}):
        with pytest.raises(RuntimeError, match="numpy"):
            service.suggest([0.1, 0.2, 0.3])


def test_suggest_with_results():
    """suggest() returns tag suggestions based on neighbors."""

    mock_index = MagicMock()
    mock_index.is_trained = True
    mock_index.search.return_value = [("id-1", 0.9), ("id-2", 0.8)]

    mock_storage = MagicMock()
    mock_storage.get_tags.side_effect = [
        ["python", "cli"],
        ["python", "web"],
    ]

    mock_config = MagicMock()
    mock_config.top_k = 5
    mock_config.min_frequency = 1

    service = AutoTagService(
        vector_index=mock_index,
        storage=mock_storage,
        config=mock_config,
    )

    result = service.suggest([0.1, 0.2, 0.3])
    assert "python" in result


def test_suggest_filters_by_min_frequency():
    """suggest() filters tags below min_frequency."""

    mock_index = MagicMock()
    mock_index.is_trained = True
    mock_index.search.return_value = [("id-1", 0.9), ("id-2", 0.8)]

    mock_storage = MagicMock()
    mock_storage.get_tags.side_effect = [
        ["python"],
        ["python"],
    ]

    mock_config = MagicMock()
    mock_config.top_k = 5
    mock_config.min_frequency = 3  # Higher than actual count

    service = AutoTagService(
        vector_index=mock_index,
        storage=mock_storage,
        config=mock_config,
    )

    result = service.suggest([0.1, 0.2, 0.3])
    assert result == []  # python appears twice but min is 3


def test_suggest_normalizes_tags():
    """suggest() normalizes tags to lowercase and strips whitespace."""

    mock_index = MagicMock()
    mock_index.is_trained = True
    mock_index.search.return_value = [("id-1", 0.9)]

    mock_storage = MagicMock()
    mock_storage.get_tags.return_value = ["  Python  ", "CLI", ""]

    mock_config = MagicMock()
    mock_config.top_k = 5
    mock_config.min_frequency = 1

    service = AutoTagService(
        vector_index=mock_index,
        storage=mock_storage,
        config=mock_config,
    )

    result = service.suggest([0.1, 0.2, 0.3])
    assert "python" in result
    assert "cli" in result
    assert "" not in result


def test_suggest_sorts_by_frequency():
    """suggest() sorts tags by frequency then alphabetically."""

    mock_index = MagicMock()
    mock_index.is_trained = True
    mock_index.search.return_value = [("id-1", 0.9), ("id-2", 0.8), ("id-3", 0.7)]

    mock_storage = MagicMock()
    mock_storage.get_tags.side_effect = [
        ["python", "cli"],
        ["python", "web"],
        ["python"],
    ]

    mock_config = MagicMock()
    mock_config.top_k = 5
    mock_config.min_frequency = 1

    service = AutoTagService(
        vector_index=mock_index,
        storage=mock_storage,
        config=mock_config,
    )

    result = service.suggest([0.1, 0.2, 0.3])
    # python appears 3 times, cli and web appear once each
    assert result[0] == "python"
