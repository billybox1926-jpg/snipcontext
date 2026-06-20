"""Auto-tag suggestions using the existing FAISS index and storage."""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    from snipcontext.core.search import VectorIndex
    from snipcontext.core.storage import StorageEngine

from snipcontext.config.settings import AutoTagConfig

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SnippetNeighbor:
    snippet_id: str
    score: float


@dataclass
class AutoTagService:
    vector_index: VectorIndex = field(repr=False)
    storage: StorageEngine = field(repr=False)
    config: AutoTagConfig = field(default_factory=AutoTagConfig)

    def suggest(self, embedding: Sequence[float]) -> list[str]:
        try:
            import numpy as np
        except ModuleNotFoundError as exc:
            raise RuntimeError("numpy is required for autotag suggestions") from exc

        if not self.vector_index.is_trained:
            return []

        vec = np.asarray(embedding, dtype=np.float32).reshape(1, -1)
        raw = self.vector_index.search(vec, top_k=self.config.top_k + 1, min_score=0.0)
        neighbors = [SnippetNeighbor(sid, score) for sid, score in raw]

        tag_freq: dict[str, int] = defaultdict(int)
        for neighbor in neighbors:
            for tag in self.storage.get_tags(neighbor.snippet_id):
                normalized = tag.strip().lower()
                if normalized:
                    tag_freq[normalized] += 1

        candidates = [tag for tag, count in tag_freq.items() if count >= self.config.min_frequency]
        candidates.sort(key=lambda t: (-tag_freq[t], t))
        return candidates


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
