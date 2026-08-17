"""Tests for core/index_backends.py."""

import tempfile
from pathlib import Path

import numpy as np
import pytest

from snipcontext.core.index_backends import IndexBackend, KeywordOnlyBackend


def test_keyword_only_backend_add():
    """KeywordOnlyBackend.add() is a no-op."""
    backend = KeywordOnlyBackend()
    backend.add(np.array([[1.0, 2.0]]), ["id-1"])


def test_keyword_only_backend_search():
    """KeywordOnlyBackend.search() returns empty list."""
    backend = KeywordOnlyBackend()
    result = backend.search(np.array([[1.0, 2.0]]), k=5)
    assert result == []


def test_keyword_only_backend_train():
    """KeywordOnlyBackend.train() is a no-op."""
    backend = KeywordOnlyBackend()
    backend.train(np.array([[1.0, 2.0]]))


def test_keyword_only_backend_remove():
    """KeywordOnlyBackend.remove() is a no-op."""
    backend = KeywordOnlyBackend()
    backend.remove(["id-1"])


def test_keyword_only_backend_save():
    """KeywordOnlyBackend.save() is a no-op."""
    backend = KeywordOnlyBackend()
    with tempfile.NamedTemporaryFile() as f:
        backend.save(Path(f.name))


def test_keyword_only_backend_load():
    """KeywordOnlyBackend.load() returns False."""
    backend = KeywordOnlyBackend()
    with tempfile.NamedTemporaryFile() as f:
        result = backend.load(Path(f.name))
    assert result is False


def test_keyword_only_backend_is_trained():
    """KeywordOnlyBackend.is_trained returns False."""
    backend = KeywordOnlyBackend()
    assert backend.is_trained is False


def test_keyword_only_backend_count():
    """KeywordOnlyBackend.count returns 0."""
    backend = KeywordOnlyBackend()
    assert backend.count == 0


def test_keyword_only_backend_snippet_ids():
    """KeywordOnlyBackend.snippet_ids returns empty list."""
    backend = KeywordOnlyBackend()
    assert backend.snippet_ids == []


def test_index_backend_is_abstract():
    """IndexBackend cannot be instantiated directly."""
    with pytest.raises(TypeError):
        IndexBackend()
