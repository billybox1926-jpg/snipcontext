from unittest.mock import MagicMock

import pytest

from snipcontext.core.index_backends import _create_backend
from snipcontext.config.settings import Config


def _config(threshold: int = 10, auto_switch: bool = True) -> Config:
    cfg = Config()
    cfg.search.auto_index_threshold = int(threshold)
    cfg.search.auto_switch = bool(auto_switch)
    cfg.search.index_type = "flat"
    return cfg


@pytest.mark.parametrize(
    "snippet_count,expected",
    [
        (5, "FlatIndexBackend"),
        (10, "FlatIndexBackend"),
        (11, "IVFPQIndexBackend"),
        (20, "IVFPQIndexBackend"),
    ],
)
def test_auto_switch_uses_correct_backend(snippet_count: int, expected: str, monkeypatch):
    cfg = _config(threshold=10, auto_switch=True)
    flat_cls = type("FlatIndexBackend", (), {})
    ivfpq_cls = type("IVFPQIndexBackend", (), {})
    monkeypatch.setattr(
        "snipcontext.core.index_backends.FlatIndexBackend",
        MagicMock(return_value=MagicMock(__class__=flat_cls)),
    )
    monkeypatch.setattr(
        "snipcontext.core.index_backends.IVFPQIndexBackend",
        MagicMock(return_value=MagicMock(__class__=ivfpq_cls)),
    )
    monkeypatch.setattr("snipcontext.core.index_backends._require_faiss", lambda: None)
    backend = _create_backend(cfg, dimension=8, snippet_count=snippet_count)
    assert backend.__class__.__name__ == expected


def test_auto_switch_disabled_remains_flat_even_above_threshold(monkeypatch):
    cfg = _config(threshold=10, auto_switch=False)
    flat_cls = type("FlatIndexBackend", (), {})
    ivfpq_cls = type("IVFPQIndexBackend", (), {})
    monkeypatch.setattr(
        "snipcontext.core.index_backends.FlatIndexBackend",
        MagicMock(return_value=MagicMock(__class__=flat_cls)),
    )
    monkeypatch.setattr(
        "snipcontext.core.index_backends.IVFPQIndexBackend",
        MagicMock(return_value=MagicMock(__class__=ivfpq_cls)),
    )
    monkeypatch.setattr("snipcontext.core.index_backends._require_faiss", lambda: None)
    backend = _create_backend(cfg, dimension=8, snippet_count=20)
    assert backend.__class__.__name__ == "FlatIndexBackend"
