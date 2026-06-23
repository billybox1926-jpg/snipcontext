"""Unit tests for the vector index backend abstraction."""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pytest
from snipcontext.config.settings import Config, SearchConfig
from snipcontext.core.index_backends import (
    FlatIndexBackend,
    HNSWIndexBackend,
    IVFPQIndexBackend,
    KeywordOnlyBackend,
    _create_backend,
)


def _rng():
    return np.random.RandomState(0)


def _vecs(n=200, dim=16):
    data = _rng().randn(n, dim).astype("float32")
    data /= np.linalg.norm(data, axis=1, keepdims=True)
    return data


class TestKeywordOnlyBackend:
    def test_noop_methods(self):
        backend = KeywordOnlyBackend()
        assert not backend.is_trained
        assert backend.count == 0
        assert backend.snippet_ids == []
        backend.add(np.zeros((1, 4), dtype=np.float32), ["a"])
        assert backend.search(np.zeros((1, 4), dtype=np.float32), 1) == []
        backend.remove(["a"])
        backend.save(Path("ignore"))
        assert not backend.load(Path("ignore"))

    def test_train_is_noop(self):
        backend = KeywordOnlyBackend()
        backend.train(np.zeros((10, 4), dtype=np.float32))


class TestFlatIndexBackend:
    def test_add_search(self):
        backend = FlatIndexBackend(16)
        data = _vecs(20, 16)
        backend.add(data, [f"s{i}" for i in range(20)])
        assert backend.count == 20
        assert backend.is_trained is True
        q = np.ascontiguousarray(data[:1], dtype=np.float32)
        out = backend.search(q, 5)
        assert len(out) == 5
        assert out[0][0] == "s0"
        assert abs(out[0][1] - 1.0) < 1e-4

    def test_remove(self):
        backend = FlatIndexBackend(16)
        data = _vecs(10, 16)
        backend.add(data, [f"s{i}" for i in range(10)])
        backend.remove(["s2", "s7"])
        assert backend.count == 8
        assert "s2" not in backend.snippet_ids
        assert "s7" not in backend.snippet_ids

    def test_remove_empty_ids(self):
        backend = FlatIndexBackend(16)
        backend.remove([])

    def test_remove_ids_not_found(self):
        backend = FlatIndexBackend(16)
        data = _vecs(10, 16)
        backend.add(data, [f"s{i}" for i in range(10)])
        backend.remove(["s999"])
        assert backend.count == 10

    def test_add_shape_mismatch(self):
        backend = FlatIndexBackend(16)
        with pytest.raises(ValueError):
            backend.add(_vecs(5, 8), ["a"] * 5)

    def test_search_skip_negative_indices(self):
        backend = FlatIndexBackend(16)
        q = np.zeros((1, 16), dtype=np.float32)
        assert backend.search(q, 1) == []

    def test_save_load_roundtrip(self, tmp_path: Path):
        backend = FlatIndexBackend(16)
        data = _vecs(20, 16)
        backend.add(data, [f"s{i}" for i in range(20)])
        backend.save(tmp_path)
        loaded = FlatIndexBackend(16)
        assert loaded.load(tmp_path) is True
        assert loaded.count == 20
        assert loaded.snippet_ids == backend.snippet_ids

    def test_load_missing_files(self, tmp_path: Path):
        backend = FlatIndexBackend(16)
        assert backend.load(tmp_path) is False


class TestHNSWIndexBackend:
    def test_add_search(self):
        backend = HNSWIndexBackend(16, m=8, ef_construction=40, ef_search=10)
        data = _vecs(50, 16)
        backend.add(data, [f"s{i}" for i in range(50)])
        assert backend.count == 50
        q = np.ascontiguousarray(data[:1], dtype=np.float32)
        out = backend.search(q, 5)
        assert len(out) == 5

    def test_remove_tombstone(self):
        backend = HNSWIndexBackend(16, m=8, ef_construction=40, ef_search=10)
        data = _vecs(25, 16)
        ids = [f"s{i}" for i in range(25)]
        backend.add(data, ids)
        backend.remove(["s5", "s10"])
        assert "s5" not in backend.snippet_ids
        assert "s10" not in backend.snippet_ids

    def test_search_skips_removed(self):
        backend = HNSWIndexBackend(16, m=8, ef_construction=40, ef_search=10)
        data = _vecs(10, 16)
        backend.add(data, [f"s{i}" for i in range(10)])
        backend.remove(["s0"])
        q = np.ascontiguousarray(data[0:1], dtype=np.float32)
        out = backend.search(q, 3)
        assert all(sid != "s0" for sid, _ in out)

    def test_add_shape_mismatch(self):
        backend = HNSWIndexBackend(16, m=8, ef_construction=40, ef_search=10)
        with pytest.raises(ValueError):
            backend.add(_vecs(5, 8), ["a"] * 5)

    def test_save_load_roundtrip(self, tmp_path: Path):
        backend = HNSWIndexBackend(16, m=8, ef_construction=40, ef_search=10)
        data = _vecs(30, 16)
        backend.add(data, [f"s{i}" for i in range(30)])
        backend.save(tmp_path)
        loaded = HNSWIndexBackend(16, m=8, ef_construction=40, ef_search=10)
        assert loaded.load(tmp_path) is True
        assert loaded.count == 30
        assert loaded.snippet_ids == backend.snippet_ids

    def test_load_missing_files(self, tmp_path: Path):
        backend = HNSWIndexBackend(16, m=8, ef_construction=40, ef_search=10)
        assert backend.load(tmp_path) is False


class TestIVFPQIndexBackend:
    def test_train_add_search(self):
        backend = IVFPQIndexBackend(
            dimension=16,
            nlist=8,
            pq_m=4,
            pq_nbits=8,
            nprobe=2,
        )
        data = _vecs(400, 16)
        backend.train(data)
        backend.add(data[:100], [f"s{i}" for i in range(100)])
        assert backend.count == 100
        q = np.ascontiguousarray(data[:1], dtype=np.float32)
        out = backend.search(q, 5)
        assert len(out) == 5

    def test_train_idempotent(self):
        backend = IVFPQIndexBackend(
            dimension=16,
            nlist=8,
            pq_m=4,
            pq_nbits=8,
            nprobe=2,
        )
        data = _vecs(400, 16)
        backend.train(data)
        backend.train(data)

    def test_add_before_train_raises(self):
        backend = IVFPQIndexBackend(
            dimension=16,
            nlist=8,
            pq_m=4,
            pq_nbits=8,
            nprobe=2,
        )
        data = _vecs(10, 16)
        with pytest.raises(RuntimeError):
            backend.add(data, [f"s{i}" for i in range(10)])

    def test_remove(self):
        backend = IVFPQIndexBackend(
            dimension=16,
            nlist=8,
            pq_m=4,
            pq_nbits=8,
            nprobe=2,
        )
        data = _vecs(400, 16)
        backend.train(data)
        backend.add(data[:50], [f"s{i}" for i in range(50)])
        backend.remove(["s5", "s6"])
        assert backend.count == 48
        assert "s5" not in backend.snippet_ids
        assert "s6" not in backend.snippet_ids

    def test_remove_empty_ids(self):
        backend = IVFPQIndexBackend(
            dimension=16,
            nlist=8,
            pq_m=4,
            pq_nbits=8,
            nprobe=2,
        )
        backend.remove([])

    def test_save_load_roundtrip(self, tmp_path: Path):
        backend = IVFPQIndexBackend(
            dimension=16,
            nlist=8,
            pq_m=4,
            pq_nbits=8,
            nprobe=2,
        )
        data = _vecs(400, 16)
        backend.train(data)
        backend.add(data[:50], [f"s{i}" for i in range(50)])
        backend.save(tmp_path)
        loaded = IVFPQIndexBackend(
            dimension=16,
            nlist=8,
            pq_m=4,
            pq_nbits=8,
            nprobe=2,
        )
        assert loaded.load(tmp_path) is True
        assert loaded.count == 50
        assert loaded.snippet_ids == backend.snippet_ids

    def test_load_missing_files(self, tmp_path: Path):
        backend = IVFPQIndexBackend(
            dimension=16,
            nlist=8,
            pq_m=4,
            pq_nbits=8,
            nprobe=2,
        )
        assert backend.load(tmp_path) is False


class TestFactory:
    def test_flat_factory(self):
        backend = _create_backend(Config(search=SearchConfig(index_type="flat")), 16)
        assert isinstance(backend, FlatIndexBackend)

    def test_hnsw_factory(self):
        backend = _create_backend(Config(search=SearchConfig(index_type="hnsw")), 16)
        assert isinstance(backend, HNSWIndexBackend)
        assert backend._ef_search == 16

    def test_ivfpq_factory(self):
        backend = _create_backend(Config(search=SearchConfig(index_type="ivfpq")), 16)
        assert isinstance(backend, IVFPQIndexBackend)

    def test_auto_switch_flat_to_ivfpq(self):
        config = Config(search=SearchConfig(index_type="flat", auto_index_threshold=1000))
        backend = _create_backend(config, 16, snippet_count=5000)
        assert isinstance(backend, IVFPQIndexBackend)

    def test_auto_switch_respects_user_choice(self):
        config = Config(search=SearchConfig(index_type="hnsw", auto_index_threshold=1000))
        backend = _create_backend(config, 16, snippet_count=5000)
        assert isinstance(backend, HNSWIndexBackend)

    def test_auto_switch_disabled(self):
        config = Config(
            search=SearchConfig(index_type="flat", auto_index_threshold=1000, auto_switch=False)
        )
        backend = _create_backend(config, 16, snippet_count=5000)
        assert isinstance(backend, FlatIndexBackend)

    def test_auto_switch_logs_message(self, caplog):
        caplog.set_level(logging.INFO)
        config = Config(search=SearchConfig(index_type="flat", auto_index_threshold=1000))
        _create_backend(config, 16, snippet_count=5000)
        assert any(
            "Automatically switching to IVFPQ index" in record.message for record in caplog.records
        )

    def test_unknown_fallback_to_flat(self, caplog):
        class FakeConfig:
            class SearchConfig:
                index_type = "unknown"
                auto_index_threshold = 5000

        config = FakeConfig()
        config.search = FakeConfig.SearchConfig()  # type: ignore[attr-defined]
        backend = _create_backend(config, 16)
        assert isinstance(backend, FlatIndexBackend)
        assert any("Unknown index_type" in record.message for record in caplog.records)
