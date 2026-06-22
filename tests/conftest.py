"""Shared test fixtures for SnipContext."""

from __future__ import annotations

import tempfile
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from snipcontext.config.settings import Config, StorageConfig, reset_config
from snipcontext.plugins.base import Plugin, PluginManifest


@pytest.fixture(autouse=True)
def reset_config_cache():
    """Reset the config singleton between tests."""
    reset_config()
    # Also reset the shared CLI context singleton
    from snipcontext.cli.context import reset_context

    reset_context()
    yield
    reset_config()
    reset_context()


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


@contextmanager
def _patched_entry_points(entries: dict[str, list[MagicMock]]) -> Generator[None, None, None]:
    """Patch importlib.metadata.entry_points() to return a controlled fake."""
    fake_eps = MagicMock()

    def fake_select(group: str | None = None) -> list[MagicMock]:
        if group is None:
            return []
        return entries.get(group, [])

    fake_eps.select = MagicMock(side_effect=fake_select)
    fake_eps.__iter__ = MagicMock(side_effect=lambda: iter(sum(entries.values(), [])))
    with patch("importlib.metadata.entry_points", return_value=fake_eps):
        yield


@pytest.fixture
def temp_entry_points():
    """Register temporary fake entry points with a context manager.

    Usage:
        with temp_entry_points({"snipcontext.plugins": [ep1], "snipcontext.providers": [ep2]}):
            ...
    """
    return _patched_entry_points


@pytest.fixture
def fake_plugin_factory():
    """Return a factory that builds fake Plugin entry points for tests."""
    built: list[MagicMock] = []

    def factory(
        name: str,
        *,
        plugin_cls: type[Plugin] | None = None,
        api_version: str = "0.3.0",
        requires: list[str] | None = None,
        group: str = "snipcontext.plugins",
    ) -> MagicMock:
        cls = plugin_cls or type(
            name,
            (Plugin,),
            {
                "manifest": PluginManifest(
                    name=name,
                    api_version=api_version,
                    requires=requires or [],
                ),
                "on_load": lambda self: None,
                "on_shutdown": lambda self: None,
                "on_snippet_saved": lambda self, snippet: None,
                "on_snippet_loaded": lambda self, snippet: None,
                "on_search": lambda self, query, results: results,
                "on_config_change": lambda self, new_config: None,
                "get_import_sources": lambda self: {},
            },
        )
        ep = MagicMock()
        ep.name = name
        ep.group = group
        ep.load.return_value = cls
        built.append(ep)
        return ep

    factory.reset = lambda: built.clear()  # noqa
    factory.built = built
    return factory


@pytest.fixture
def mock_embeddings(mocker):
    """Patch the embedding engine to return deterministic vectors.

    Defaults to fixed-dimension float32 vectors when no explicit vectors
    are seeded, so search tests stay fast and offline.
    """
    from snipcontext.core.search import EmbeddingEngine

    def _fake_encode(texts: list[str], *args: Any, **kwargs: Any) -> Any:
        try:
            import numpy as np
        except ImportError as exc:  # pragma: no cover - safety net
            raise RuntimeError("numpy is required for mock embeddings") from exc
        dim = kwargs.pop("dimension", 16)
        return np.zeros((len(texts), dim), dtype=np.float32)

    def _fake_encode_query(query: str, *args: Any, **kwargs: Any) -> Any:
        import numpy as np

        dim = kwargs.pop("dimension", 16)
        return np.zeros((1, dim), dtype=np.float32)

    mocker.patch.object(EmbeddingEngine, "encode", side_effect=_fake_encode)
    mocker.patch.object(EmbeddingEngine, "encode_query", side_effect=_fake_encode_query)
    mocker.patch.object(
        EmbeddingEngine,
        "dimension",
        new_callable=mocker.PropertyMock,
        return_value=16,
    )
    return _fake_encode


@pytest.fixture
def mock_provider_apis(mocker):
    """Patch outbound HTTP calls for provider API roundtrip tests.

    Returns a request factory registry. Tests register expected responses
    by provider name and callable matcher; unmatched calls raise.
    """
    responses: dict[str, Any] = {}
    sent = []

    class FakeResponse:
        def __init__(self, status_code: int = 200, payload: Any = None) -> None:
            self.status_code = status_code
            self._payload = payload or {}

        def json(self) -> Any:
            return self._payload

        def raise_for_status(self) -> None:
            if self.status_code >= 400:
                raise RuntimeError(f"HTTP {self.status_code}")

        @property
        def text(self) -> str:
            import json

            return json.dumps(self._payload)

    def fake_request(method: str, url: str, *args: Any, **kwargs: Any) -> FakeResponse:
        sent.append((method, url, args, kwargs))
        for key, handler in responses.items():
            if key in url:
                return handler(url, *args, **kwargs)
        raise RuntimeError(f"No mock registered for URL: {url}")

    try:
        import requests as http_client

        mocker.patch.object(http_client.Session, "request", side_effect=fake_request)
    except ModuleNotFoundError:  # pragma: no cover - requests optional
        pass

    mocker.patch(
        "urllib.request.urlopen",
        side_effect=lambda req, **_: (_ for _ in ()).throw(RuntimeError("urlopen not mocked")),
    )

    registry = {}
    factory = type("Factory", (), {})

    def register(provider: str, handler: Any) -> None:
        responses[provider] = handler
        registry[provider] = handler

    def reset() -> None:
        responses.clear()
        registry.clear()
        sent.clear()

    factory.register = register
    factory.reset = reset
    factory.sent = sent
    factory.FakeResponse = FakeResponse
    factory.responses = responses
    return factory


@pytest.fixture
def mock_vector_store(mocker):
    """Provide an in-memory vector store double for search tests."""
    from snipcontext.core.search import VectorIndex

    fake_index = MagicMock()
    fake_index.is_trained = True
    fake_index.count = 0

    def fake_search(query, top_k=5):
        return []

    fake_index.search = MagicMock(side_effect=fake_search)
    mocker.patch.object(VectorIndex, "build", return_value=None)
    mocker.patch.object(VectorIndex, "search", side_effect=fake_search)
    return fake_index
