"""Vector index backend abstraction.

Provides a pluggable ``IndexBackend`` interface so ``VectorIndex`` can delegate
to different FAISS strategies (flat, HNSW, IVF, IVFPQ) or to a no-op fallback
when semantic dependencies are unavailable.
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    import faiss

logger = logging.getLogger(__name__)


class IndexBackend(ABC):
    """Contract for vector index backends."""

    @abstractmethod
    def add(self, vectors: np.ndarray, ids: list[str]) -> None:
        """Index a batch of vectors with their snippet IDs."""

    @abstractmethod
    def search(self, query: np.ndarray, k: int) -> list[tuple[str, float]]:
        """Return top-k ``(snippet_id, score)`` pairs for the query vector."""

    @abstractmethod
    def train(self, vectors: np.ndarray) -> None:
        """Train the index if required by the backend implementation."""

    @abstractmethod
    def remove(self, ids: list[str]) -> None:
        """Remove the given snippet IDs from the index."""

    @abstractmethod
    def save(self, path: Path) -> None:
        """Persist the index and ID mapping to ``path``."""

    @abstractmethod
    def load(self, path: Path) -> bool:
        """Restore state from ``path``; return ``True`` on success."""

    @property
    @abstractmethod
    def is_trained(self) -> bool:
        """Indicate whether the index is ready for search."""

    @property
    @abstractmethod
    def count(self) -> int:
        """Total vectors currently indexed."""

    @property
    @abstractmethod
    def snippet_ids(self) -> list[str]:
        """Ordered list of snippet IDs matching the internal FAISS order."""


class KeywordOnlyBackend(IndexBackend):
    """Graceful fallback when FAISS is not installed."""

    def add(self, vectors: np.ndarray, ids: list[str]) -> None:
        return None

    def search(self, query: np.ndarray, k: int) -> list[tuple[str, float]]:
        return []

    def train(self, vectors: np.ndarray) -> None:
        return None

    def remove(self, ids: list[str]) -> None:
        return None

    def save(self, path: Path) -> None:
        return None

    def load(self, path: Path) -> bool:
        return False

    @property
    def is_trained(self) -> bool:
        return False

    @property
    def count(self) -> int:
        return 0

    @property
    def snippet_ids(self) -> list[str]:
        return []


class FlatIndexBackend(IndexBackend):
    """Exact inner-product index via ``faiss.IndexFlatIP``."""

    def __init__(self, dimension: int) -> None:
        try:
            import faiss
        except ImportError as exc:
            raise ImportError(
                "Semantic search requires the 'faiss-cpu' package. "
                "Install it with: pip install snipcontext[semantic]"
            ) from exc
        self._index: faiss.Index = faiss.IndexFlatIP(dimension)
        self._id_map: list[str] = []
        self._id_to_idx: dict[str, int] = {}
        self._dimension = int(dimension)

    def add(self, vectors: np.ndarray, ids: list[str]) -> None:
        vectors = np.ascontiguousarray(vectors, dtype=np.float32)
        if vectors.ndim != 2 or vectors.shape[1] != self._dimension:
            raise ValueError(
                f"Expected vectors with shape (*, {self._dimension}); got {vectors.shape}"
            )
        self._index.add(vectors)
        start = len(self._id_map)
        self._id_map.extend(ids)
        self._id_to_idx.update({sid: start + i for i, sid in enumerate(ids)})

    def search(self, query: np.ndarray, k: int) -> list[tuple[str, float]]:
        scores, indices = self._index.search(np.ascontiguousarray(query, dtype=np.float32), k)
        results: list[tuple[str, float]] = []
        for score, idx in zip(scores[0], indices[0], strict=False):
            if idx < 0 or idx >= len(self._id_map):
                continue
            results.append((self._id_map[int(idx)], float(score)))
        return results

    def train(self, vectors: np.ndarray) -> None:
        return None

    def remove(self, ids: list[str]) -> None:
        try:
            import faiss
        except ImportError as exc:
            raise ImportError("faiss is required for index removal") from exc
        if not ids:
            return
        idxs = [self._id_to_idx.pop(sid) for sid in ids if sid in self._id_to_idx]
        if not idxs:
            return
        selector = faiss.IDSelectorBatch(idxs)
        self._index.remove_ids(selector)
        kept = [sid for sid in self._id_map if sid not in ids]
        self._id_map = kept
        self._id_to_idx = {sid: i for i, sid in enumerate(self._id_map)}

    def save(self, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)
        try:
            import faiss
        except ImportError as exc:
            raise ImportError("faiss is required for index persistence") from exc
        faiss.write_index(self._index, str(path / "vector.faiss"))
        (path / "idmap.json").write_text(json.dumps(self._id_map), encoding="utf-8")
        logger.debug("Saved flat index to %s", path)

    def load(self, path: Path) -> bool:
        try:
            import faiss
        except ImportError as exc:
            raise ImportError("faiss is required for index loading") from exc
        index_file = path / "vector.faiss"
        idmap_file = path / "idmap.json"
        if not index_file.exists() or not idmap_file.exists():
            logger.debug("Flat index files not found at %s", path)
            return False
        try:
            self._index = faiss.read_index(str(index_file))
            self._id_map = json.loads(idmap_file.read_text(encoding="utf-8"))
            if self._index.ntotal != len(self._id_map):
                logger.warning(
                    "Flat index ID map length mismatch: %d vectors vs %d IDs",
                    self._index.ntotal,
                    len(self._id_map),
                )
                return False
            self._id_to_idx = {sid: i for i, sid in enumerate(self._id_map)}
            return True
        except Exception as exc:
            logger.warning("Failed to load flat index from %s: %s", path, exc)
            return False

    @property
    def is_trained(self) -> bool:
        return self._index is not None and self._index.ntotal > 0

    @property
    def count(self) -> int:
        return int(self._index.ntotal if self._index else 0)

    @property
    def snippet_ids(self) -> list[str]:
        return list(self._id_map)


class HNSWIndexBackend(IndexBackend):
    """HNSW approximate nearest-neighbor index via ``faiss.IndexHNSWFlat``."""

    def __init__(self, dimension: int, m: int, ef_construction: int, ef_search: int) -> None:
        try:
            import faiss
        except ImportError as exc:
            raise ImportError(
                "Semantic search requires the 'faiss-cpu' package. "
                "Install it with: pip install snipcontext[semantic]"
            ) from exc
        self._index: faiss.Index = faiss.IndexHNSWFlat(dimension, m)
        self._index.hnsw.efConstruction = ef_construction
        self._ef_search = ef_search
        self._id_map: list[str] = []
        self._id_to_idx: dict[str, int] = {}
        self._removed: set[str] = set()
        self._dimension = int(dimension)

    def add(self, vectors: np.ndarray, ids: list[str]) -> None:
        vectors = np.ascontiguousarray(vectors, dtype=np.float32)
        if vectors.ndim != 2 or vectors.shape[1] != self._dimension:
            raise ValueError(
                f"Expected vectors with shape (*, {self._dimension}); got {vectors.shape}"
            )
        self._index.add(vectors)
        start = len(self._id_map)
        self._id_map.extend(ids)
        self._id_to_idx.update({sid: start + i for i, sid in enumerate(ids)})

    def search(self, query: np.ndarray, k: int) -> list[tuple[str, float]]:
        self._index.hnsw.efSearch = self._ef_search
        scores, indices = self._index.search(np.ascontiguousarray(query, dtype=np.float32), k)
        results: list[tuple[str, float]] = []
        for score, idx in zip(scores[0], indices[0], strict=False):
            if idx < 0 or idx >= len(self._id_map):
                continue
            sid = self._id_map[int(idx)]
            if sid in self._removed:
                continue
            results.append((sid, float(score)))
        return results

    def train(self, vectors: np.ndarray) -> None:
        return None

    def remove(self, ids: list[str]) -> None:
        if not ids:
            return
        for snippet_id in ids:
            self._removed.add(snippet_id)
            self._id_to_idx.pop(snippet_id, None)
        if self._removed:
            logger.debug("HNSW tombstone active (%d removed)", len(self._removed))

    def save(self, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)
        try:
            import faiss
        except ImportError as exc:
            raise ImportError("faiss is required for index persistence") from exc
        faiss.write_index(self._index, str(path / "vector.faiss"))
        payload = {
            "id_map": self._id_map,
            "removed": sorted(self._removed),
        }
        (path / "hnsw_state.json").write_text(json.dumps(payload), encoding="utf-8")
        logger.debug("Saved HNSW index to %s", path)

    def load(self, path: Path) -> bool:
        try:
            import faiss
        except ImportError as exc:
            raise ImportError("faiss is required for index loading") from exc
        index_file = path / "vector.faiss"
        state_file = path / "hnsw_state.json"
        if not index_file.exists() or not state_file.exists():
            logger.debug("HNSW index files not found at %s", path)
            return False
        try:
            self._index = faiss.read_index(str(index_file))
            data = json.loads(state_file.read_text(encoding="utf-8"))
            self._id_map = data.get("id_map", [])
            self._removed = set(data.get("removed", []))
            self._id_to_idx = {
                sid: i for i, sid in enumerate(self._id_map) if sid not in self._removed
            }
            return True
        except Exception as exc:
            logger.warning("Failed to load HNSW index from %s: %s", path, exc)
            return False

    @property
    def is_trained(self) -> bool:
        return self._index is not None and self._index.ntotal > 0

    @property
    def count(self) -> int:
        return int(self._index.ntotal if self._index else 0)

    @property
    def snippet_ids(self) -> list[str]:
        return [sid for sid in self._id_map if sid not in self._removed]


class IVFPQIndexBackend(IndexBackend):
    """Compressed IVF+PQ index."""

    def __init__(
        self,
        dimension: int,
        nlist: int,
        pq_m: int,
        pq_nbits: int,
        nprobe: int,
    ) -> None:
        try:
            import faiss
        except ImportError as exc:
            raise ImportError(
                "Semantic search requires the 'faiss-cpu' package. "
                "Install it with: pip install snipcontext[semantic]"
            ) from exc
        quantizer = faiss.IndexFlatIP(dimension)
        self._index: faiss.Index = faiss.IndexIVFPQ(quantizer, dimension, nlist, pq_m, pq_nbits)
        self._nprobe = int(nprobe)
        self._dimension = int(dimension)
        self._id_map: list[str] = []
        self._id_to_idx: dict[str, int] = {}

    def add(self, vectors: np.ndarray, ids: list[str]) -> None:
        vectors = np.ascontiguousarray(vectors, dtype=np.float32)
        if vectors.ndim != 2 or vectors.shape[1] != self._dimension:
            raise ValueError(
                f"Expected vectors with shape (*, {self._dimension}); got {vectors.shape}"
            )
        if not self.is_trained:
            raise RuntimeError("IVFPQ index must be trained before adding vectors")
        self._index.add(vectors)
        start = len(self._id_map)
        self._id_map.extend(ids)
        self._id_to_idx.update({sid: start + i for i, sid in enumerate(ids)})

    def search(self, query: np.ndarray, k: int) -> list[tuple[str, float]]:
        self._index.nprobe = self._nprobe
        scores, indices = self._index.search(np.ascontiguousarray(query, dtype=np.float32), k)
        results: list[tuple[str, float]] = []
        for score, idx in zip(scores[0], indices[0], strict=False):
            if idx < 0 or idx >= len(self._id_map):
                continue
            results.append((self._id_map[int(idx)], float(score)))
        return results

    def train(self, vectors: np.ndarray) -> None:
        if not self.is_trained:
            training = np.ascontiguousarray(vectors, dtype=np.float32)
            self._index.train(training)

    def remove(self, ids: list[str]) -> None:
        if not ids:
            return
        try:
            import faiss
        except ImportError as exc:
            raise ImportError("faiss is required for index removal") from exc
        idxs = [self._id_to_idx.pop(sid) for sid in ids if sid in self._id_to_idx]
        if not idxs:
            return
        selector = faiss.IDSelectorBatch(idxs)
        self._index.remove_ids(selector)
        kept = [sid for sid in self._id_map if sid not in ids]
        self._id_map = kept
        self._id_to_idx = {sid: i for i, sid in enumerate(self._id_map)}

    def save(self, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)
        try:
            import faiss
        except ImportError as exc:
            raise ImportError("faiss is required for index persistence") from exc
        faiss.write_index(self._index, str(path / "vector.faiss"))
        (path / "idmap.json").write_text(json.dumps(self._id_map), encoding="utf-8")
        logger.debug("Saved IVFPQ index to %s", path)

    def load(self, path: Path) -> bool:
        try:
            import faiss
        except ImportError as exc:
            raise ImportError("faiss is required for index loading") from exc
        index_file = path / "vector.faiss"
        idmap_file = path / "idmap.json"
        if not index_file.exists() or not idmap_file.exists():
            logger.debug("IVFPQ index files not found at %s", path)
            return False
        try:
            self._index = faiss.read_index(str(index_file))
            self._id_map = json.loads(idmap_file.read_text(encoding="utf-8"))
            if self._index.ntotal != len(self._id_map):
                logger.warning(
                    "IVFPQ index ID map length mismatch: %d vectors vs %d IDs",
                    self._index.ntotal,
                    len(self._id_map),
                )
                return False
            self._id_to_idx = {sid: i for i, sid in enumerate(self._id_map)}
            return True
        except Exception as exc:
            logger.warning("Failed to load IVFPQ index from %s: %s", path, exc)
            return False

    @property
    def is_trained(self) -> bool:
        if self._index is None:
            return False
        try:
            # faiss exposes trained flag; fall back to ntotal check when unavailable.
            return bool(self._index.is_trained)  # type: ignore[attr-defined]
        except Exception:
            return self._index.ntotal > 0

    @property
    def count(self) -> int:
        return int(self._index.ntotal if self._index else 0)

    @property
    def snippet_ids(self) -> list[str]:
        return list(self._id_map)


def _create_backend(
    config,
    dimension: int,
    snippet_count: int | None = None,
    auto_switch: bool | None = None,
) -> IndexBackend:
    """Instantiate the backend indicated by ``config.search.index_type``.

    When ``index_type`` is ``flat`` and ``snippet_count`` exceeds
    ``auto_index_threshold``, the factory transparently returns an
    ``IVFPQIndexBackend`` so large collections self-optimize.
    """
    index_type = getattr(config.search, "index_type", "flat")
    threshold = getattr(config.search, "auto_index_threshold", 5000)
    if auto_switch is None:
        auto_switch = getattr(config.search, "auto_switch", True)
    if (
        index_type == "flat"
        and auto_switch
        and snippet_count is not None
        and snippet_count > threshold
    ):
        try:
            import faiss
        except ImportError:
            return FlatIndexBackend(dimension)
        logger.info(
            "Collection size exceeded threshold (%d). Automatically switching to IVFPQ index.",
            threshold,
        )
        nlist = min(int(np.sqrt(snippet_count)), 256)
        return IVFPQIndexBackend(
            dimension,
            nlist=nlist,
            pq_m=getattr(config.search, "pq_M", 8),
            pq_nbits=getattr(config.search, "pq_nbits", 8),
            nprobe=getattr(config.search, "ivf_nprobe", 8),
        )
    if index_type == "flat":
        return FlatIndexBackend(dimension)
    if index_type == "hnsw":
        return HNSWIndexBackend(
            dimension,
            m=config.search.hnsw_M,
            ef_construction=config.search.hnsw_efConstruction,
            ef_search=config.search.hnsw_efSearch,
        )
    if index_type == "ivf":
        try:
            import faiss
        except ImportError as exc:
            raise ImportError("faiss is required for IVF index") from exc
        nlist = getattr(config.search, "ivf_nlist", 128)
        quantizer = faiss.IndexFlatIP(int(dimension))
        backend = IVFPQIndexBackend.__new__(IVFPQIndexBackend)
        backend._index = faiss.IndexIVFFlat(quantizer, int(dimension), nlist)
        backend._nprobe = getattr(config.search, "ivf_nprobe", 8)
        backend._dimension = int(dimension)
        backend._id_map = []
        backend._id_to_idx = {}
        return backend
    if index_type == "ivfpq":
        return IVFPQIndexBackend(
            dimension,
            nlist=getattr(config.search, "ivf_nlist", 128),
            pq_m=getattr(config.search, "pq_M", 8),
            pq_nbits=getattr(config.search, "pq_nbits", 8),
            nprobe=getattr(config.search, "ivf_nprobe", 8),
        )
    # Unknown type -> conservative flat fallback
    logger.warning("Unknown index_type %r; falling back to flat", index_type)
    return FlatIndexBackend(dimension)
