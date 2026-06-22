"""Optional real-model integration matrix for semantic search."""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pytest
from typer.testing import CliRunner

from snipcontext.cli.app import app
from snipcontext.config.settings import Config, EmbeddingConfig, SearchConfig, StorageConfig
from snipcontext.core.models import Language, Snippet, SnippetMetadata
from snipcontext.core.search import EmbeddingEngine, HybridSearch
from snipcontext.core.storage import StorageEngine

MODEL_IDS = ["all-MiniLM-L6-v2", "BAAI/bge-small-en-v1.5"]
DEVICE_IDS = ["cpu", "cuda", "mps"]
runner = CliRunner()


def _matrix_enabled() -> bool:
    return os.environ.get("SNIPCONTEXT_RUN_MODEL_MATRIX") == "1"


def _device_available(device: str) -> bool:
    if device == "cpu":
        return True
    try:
        import torch
    except (ImportError, OSError):
        return False
    if device == "cuda":
        return bool(torch.cuda.is_available())
    if device == "mps":
        return bool(getattr(torch.backends, "mps", None) and torch.backends.mps.is_available())
    return False


def _config(temp_dir: Path, model_name: str, device: str) -> Config:
    return Config(
        storage=StorageConfig(data_dir=temp_dir, snippets_dir="snippets", index_dir="index"),
        embedding=EmbeddingConfig(model_name=model_name, device=device, batch_size=2),
        search=SearchConfig(default_mode="hybrid", min_score=0.0, top_k=3),
    )


def _snippet(snippet_id: str, title: str, content: str) -> Snippet:
    return Snippet(
        id=snippet_id,
        content=content,
        metadata=SnippetMetadata(title=title, language=Language.PYTHON),
        tags=["matrix"],
    )


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.parametrize("model_name", MODEL_IDS)
@pytest.mark.parametrize("device", DEVICE_IDS)
def test_embedding_model_device_matrix_generates_vectors_and_ranks(
    temp_dir: Path,
    model_name: str,
    device: str,
) -> None:
    if not _matrix_enabled():
        pytest.skip("set SNIPCONTEXT_RUN_MODEL_MATRIX=1 to run real embedding matrix")
    if not _device_available(device):
        pytest.skip(f"device {device!r} is not available")
    pytest.importorskip("sentence_transformers")
    pytest.importorskip("faiss")

    config = _config(temp_dir, model_name, device)
    storage = StorageEngine(config)
    target = _snippet("matrix-auth", "Auth Middleware", "FastAPI JWT authentication middleware")
    other = _snippet("matrix-css", "CSS Utility", "CSS grid layout utility classes")
    storage.save(target)
    storage.save(other)

    engine = EmbeddingEngine(config)
    vectors = engine.encode([target.to_search_text(), other.to_search_text()])
    assert vectors.shape == (2, engine.dimension)
    assert vectors.dtype == np.float32
    assert np.any(vectors != 0.0)

    searcher = HybridSearch(config)
    searcher.index_snippets([target, other])
    results = searcher.search("jwt authentication", top_k=2, min_score=0.0)
    assert results
    assert results[0].id == target.id


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.parametrize("model_name", MODEL_IDS[:1])
def test_search_cli_smoke_with_real_cpu_model(temp_dir: Path, model_name: str) -> None:
    if not _matrix_enabled():
        pytest.skip("set SNIPCONTEXT_RUN_MODEL_MATRIX=1 to run real embedding matrix")
    pytest.importorskip("sentence_transformers")
    pytest.importorskip("faiss")

    env = {
        "SNIPCONTEXT_STORAGE__DATA_DIR": str(temp_dir),
        "SNIPCONTEXT_STORAGE__SNIPPETS_DIR": "snippets",
        "SNIPCONTEXT_STORAGE__INDEX_DIR": "index",
        "SNIPCONTEXT_EMBED__MODEL_NAME": model_name,
        "SNIPCONTEXT_EMBED__DEVICE": "cpu",
        "SC_AUTO_TAG_ENABLED": "false",
        "SC_DEDUP_ENABLED": "false",
    }
    added = runner.invoke(
        app,
        ["add", "FastAPI JWT authentication middleware", "--title", "Auth Middleware"],
        env=env,
    )
    assert added.exit_code == 0, added.output

    searched = runner.invoke(app, ["search", "jwt authentication", "--limit", "1"], env=env)
    assert searched.exit_code == 0, searched.output
    assert "Auth Middleware" in searched.output
