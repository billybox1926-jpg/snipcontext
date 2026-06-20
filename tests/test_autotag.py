"""Tests for auto-tag suggestions."""

from __future__ import annotations

from snipcontext.core.auto_tag import AutoTagService


class DummyIndex:
    def __init__(self, mapping: dict[str, str]) -> None:
        self._mapping = mapping
        self.is_trained = True

    def search(
        self, _vec: object, top_k: int = 5, min_score: float = 0.0
    ) -> list[tuple[str, float]]:
        results: list[tuple[str, float]] = []
        for value in self._mapping.values():
            if len(results) >= top_k:
                break
            results.append((value, 0.5))
        return results


class DummyStorage:
    def __init__(self, tags_by_id: dict[str, list[str]]) -> None:
        self.tags_by_id = tags_by_id

    def get_tags(self, snippet_id: str) -> list[str]:
        return list(self.tags_by_id.get(snippet_id, []))


class DummyConfig:
    def __init__(self, top_k: int = 5, min_frequency: int = 2) -> None:
        self.top_k = top_k
        self.min_frequency = min_frequency


class TestAutoTagService:
    def test_suggest_empty_index(self) -> None:
        service = AutoTagService(
            vector_index=DummyIndex({}),
            storage=DummyStorage({}),
            config=DummyConfig(),
        )
        assert service.suggest([0.1, 0.2, 0.3]) == []

    def test_suggest_returns_normalized_candidates(self) -> None:
        index = DummyIndex({"alpha": "snippet-1"})
        storage = DummyStorage({"snippet-1": ["Python", "SCRIPT"]})
        service = AutoTagService(
            vector_index=index,
            storage=storage,
            config=DummyConfig(top_k=5, min_frequency=1),
        )
        suggestions = service.suggest([0.1, 0.2, 0.3])
        assert suggestions == ["python", "script"]

    def test_suggest_filters_below_min_frequency(self) -> None:
        index = DummyIndex({"alpha": "snippet-1"})
        storage = DummyStorage({"snippet-1": ["python"]})
        service = AutoTagService(
            vector_index=index,
            storage=storage,
            config=DummyConfig(min_frequency=2),
        )
        assert service.suggest([0.1, 0.2, 0.3]) == []
