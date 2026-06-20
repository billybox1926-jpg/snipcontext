"""Auto-tag suggestions using the existing FAISS index and storage."""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import numpy as np

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SnippetNeighbor:
    snippet_id: str
    score: float


@dataclass
class AutoTagService:
    vector_index: object = field(repr=False)
    storage: object = field(repr=False)
    config: object | None = field(default=None, repr=False)

    def suggest(self, embedding: list[float]) -> list[str]:
        try:
            import numpy as np  # noqa: F401
        except ModuleNotFoundError as exc:  # pragma: no cover
            raise RuntimeError("numpy is required for autotag suggestions") from exc

        vector_index = self.vector_index
        if not getattr(vector_index, "is_trained", False):
            return []

        vec = _to_numpy(embedding)
        top_k = getattr(self.config, "top_k", 5)
        min_score = 0.0
        raw = vector_index.search(vec, top_k=top_k + 1, min_score=min_score)
        neighbors = [SnippetNeighbor(sid, score) for sid, score in raw]

        tag_freq: dict[str, int] = defaultdict(int)
        for neighbor in neighbors:
            tags = _get_storage_tags(self.storage, neighbor.snippet_id)
            if not tags:
                continue
            for tag in tags:
                normalized = _normalize_tag(tag)
                if normalized:
                    tag_freq[normalized] += 1

        min_frequency = getattr(self.config, "min_frequency", 2)
        candidates = [tag for tag, count in tag_freq.items() if count >= min_frequency]
        candidates.sort(key=lambda tag: (-tag_freq[tag], tag))
        return candidates


def _to_numpy(values: list[float]) -> np.ndarray[tuple[int, ...], np.dtype[np.float32]]:
    import numpy as np

    return np.asarray(list(values), dtype=np.float32).reshape(1, -1)


def _normalize_tag(tag: str) -> str:
    return tag.strip().lower()


def _get_storage_tags(storage: object, snippet_id: str) -> tuple[str, ...]:
    try:
        return tuple(storage.get_tags(snippet_id))
    except Exception:
        return tuple()


def _build_auto_tag_smoke() -> None:
    import tempfile
    from pathlib import Path

    from snipcontext.config.settings import AutoTagConfig, Config, StorageConfig
    from snipcontext.core.models import Language, Snippet, SnippetMetadata
    from snipcontext.core.search import EmbeddingEngine, VectorIndex
    from snipcontext.core.storage import StorageEngine

    with tempfile.TemporaryDirectory() as tmp:
        config = Config(
            storage=StorageConfig(
                data_dir=Path(tmp),
                snippets_dir="snippets",
                index_dir="index",
            )
        )
        storage = StorageEngine(config)

        first = Snippet(
            content="print('alpha')\n",
            metadata=SnippetMetadata(
                title="Alpha Snippet",
                description="first snippet",
                language=Language.PYTHON,
            ),
            tags=["python", "alpha"],
        )
        second = Snippet(
            content="print('beta')\n",
            metadata=SnippetMetadata(
                title="Beta Snippet",
                description="second snippet",
                language=Language.PYTHON,
            ),
            tags=["python", "beta"],
        )
        storage.save(first)
        storage.save(second)

        vector_index = VectorIndex(config)
        embedder = EmbeddingEngine(config)
        vector_index.build([first, second], embedder)

        service = AutoTagService(
            vector_index=vector_index,
            storage=storage,
            config=AutoTagConfig(top_k=5, min_frequency=1, auto_accept=False),
        )
        embedding = embedder.encode_query("alpha snippet").flatten()
        suggestions = service.suggest(embedding.tolist())
        logger.info("suggestions: %s", suggestions)
        assert "python" in suggestions
        assert "alpha" in suggestions


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    _build_auto_tag_smoke()
