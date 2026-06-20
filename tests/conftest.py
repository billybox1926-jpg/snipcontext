"""Shared test fixtures for SnipContext."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from snipcontext.config.settings import Config, StorageConfig, reset_config


@pytest.fixture(autouse=True)
def reset_config_cache():
    """Reset the config singleton between tests."""
    reset_config()
    yield
    reset_config()


@pytest.fixture
def temp_dir():
    """Provide a temporary directory."""
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp)


@pytest.fixture
def fresh_config(temp_dir):
    """Provide a fresh Config using a temp directory."""
    config = Config(
        storage=StorageConfig(
            data_dir=temp_dir,
            snippets_dir="snippets",
            index_dir="index",
        )
    )
    return config


@pytest.fixture
def sample_python_snippet():
    """Provide a sample Python snippet."""
    from snipcontext.core.models import Language, Snippet, SnippetMetadata

    return Snippet(
        content="def factorial(n):\n    return 1 if n <= 1 else n * factorial(n - 1)",
        metadata=SnippetMetadata(
            title="Factorial Function",
            description="Recursive factorial calculation",
            language=Language.PYTHON,
        ),
        tags=["python", "recursion", "math", "algorithm"],
    )


@pytest.fixture
def sample_javascript_snippet():
    """Provide a sample JavaScript snippet."""
    from snipcontext.core.models import Language, Snippet, SnippetMetadata

    return Snippet(
        content="const debounce = (fn, ms) => {\n  let timer;\n  return (...args) => {\n    clearTimeout(timer);\n    timer = setTimeout(() => fn(...args), ms);\n  };\n};",
        metadata=SnippetMetadata(
            title="Debounce Function",
            description="Debounce utility for event handlers",
            language=Language.JAVASCRIPT,
        ),
        tags=["javascript", "utility", "events"],
    )


@pytest.fixture
def populated_storage(fresh_config, sample_python_snippet, sample_javascript_snippet):
    """Provide a storage engine pre-populated with sample snippets."""
    from snipcontext.core.storage import StorageEngine

    storage = StorageEngine(fresh_config)
    storage.save(sample_python_snippet)
    storage.save(sample_javascript_snippet)
    return storage
