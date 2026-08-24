"""Tests for the web UI router's language validation (issue #198).

``web_ui.update_snippet`` previously wrapped the language assignment in a
bare ``except Exception: pass``. Two separate defects hid behind it:

1. ``SnippetMetadata`` does not set ``validate_assignment``, so assigning a
   raw string never raised — the ``except`` was dead code and an invalid
   value was written straight to disk, breaking every later load with a
   pydantic ``ValidationError``.
2. Even a *valid* string stayed a plain ``str`` instead of being coerced to
   the ``Language`` enum, so the response serializer (which reads
   ``.value``) reported an empty language.

NOTE: ``snippets.router`` and ``web_ui.router`` both register
``PUT /snippets/{snippet_id}`` with no prefix, and ``snippets.router`` is
included first, so it shadows this handler over HTTP. These tests therefore
call the handler directly, which is the only way to exercise the fixed code
path. The route collision is tracked separately.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pytest

from snipcontext.config.settings import Config, StorageConfig
from snipcontext.core.models import Language, Snippet, SnippetMetadata
from snipcontext.core.storage import StorageEngine

fastapi = pytest.importorskip("fastapi")
from fastapi import HTTPException  # noqa: E402

from snipcontext.web.routers.web_ui import update_snippet  # noqa: E402


@pytest.fixture
def storage(tmp_path: Path) -> StorageEngine:
    config = Config(
        storage=StorageConfig(
            data_dir=tmp_path,
            snippets_dir="snippets",
            index_dir="index",
        )
    )
    return StorageEngine(config)


@pytest.fixture
def snippet_id(storage: StorageEngine) -> str:
    snippet = Snippet(
        content="def hello():\n    print('hi')",
        metadata=SnippetMetadata(
            title="Language Test",
            description="Snippet for language validation",
            language=Language.PYTHON,
        ),
        tags=["test"],
    )
    storage.save(snippet)
    return snippet.id


@pytest.fixture(autouse=True)
def _stub_broadcast(monkeypatch: Any) -> None:
    """The handler broadcasts over the websocket manager; no-op it."""

    async def _noop(*_args: Any, **_kwargs: Any) -> None:
        return None

    monkeypatch.setattr("snipcontext.web.routers.web_ui.manager.broadcast", _noop)


class TestUpdateSnippetLanguageValidation:
    """An invalid language must be rejected, not silently swallowed."""

    @pytest.mark.asyncio
    async def test_invalid_language_raises_422(
        self, storage: StorageEngine, snippet_id: str
    ) -> None:
        with pytest.raises(HTTPException) as exc_info:
            await update_snippet(snippet_id, {"language": "not-a-language"}, storage)

        assert exc_info.value.status_code == 422
        detail = str(exc_info.value.detail)
        assert "not-a-language" in detail
        # The error enumerates accepted values so a client can recover.
        assert "python" in detail

    @pytest.mark.asyncio
    async def test_invalid_language_does_not_mutate_stored_snippet(
        self, storage: StorageEngine, snippet_id: str
    ) -> None:
        with pytest.raises(HTTPException):
            await update_snippet(snippet_id, {"language": "bogus"}, storage)

        # Nothing was persisted, so the snippet still loads and is unchanged.
        reloaded = storage.get(snippet_id)
        assert reloaded.metadata.language is Language.PYTHON

    @pytest.mark.asyncio
    async def test_invalid_language_leaves_snippet_loadable(
        self, storage: StorageEngine, snippet_id: str
    ) -> None:
        """Before the fix an invalid value was written and broke every later load."""
        with pytest.raises(HTTPException):
            await update_snippet(snippet_id, {"language": "not-a-language"}, storage)

        # Would raise pydantic ValidationError on the old code path.
        assert storage.get(snippet_id) is not None
        assert len(storage.list_all()) == 1

    @pytest.mark.asyncio
    async def test_invalid_language_is_logged(
        self, storage: StorageEngine, snippet_id: str, caplog: Any
    ) -> None:
        with caplog.at_level(logging.WARNING, logger="snipcontext.web.routers.web_ui"):
            with pytest.raises(HTTPException):
                await update_snippet(snippet_id, {"language": "nope"}, storage)

        assert any("nope" in record.getMessage() for record in caplog.records), (
            f"expected a warning naming the rejected value; got {caplog.records}"
        )


class TestUpdateSnippetLanguageSuccess:
    """A valid language must actually take effect as an enum member."""

    @pytest.mark.asyncio
    async def test_valid_language_is_coerced_to_enum(
        self, storage: StorageEngine, snippet_id: str
    ) -> None:
        """Before the fix this stayed a str and serialized as ""."""
        result = await update_snippet(snippet_id, {"language": "rust"}, storage)

        assert result["language"] == "rust"
        assert storage.get(snippet_id).metadata.language is Language.RUST

    @pytest.mark.asyncio
    async def test_omitted_language_is_left_alone(
        self, storage: StorageEngine, snippet_id: str
    ) -> None:
        result = await update_snippet(snippet_id, {"title": "Renamed"}, storage)

        assert result["title"] == "Renamed"
        assert result["language"] == "python"

    @pytest.mark.asyncio
    async def test_every_language_member_is_accepted(
        self, storage: StorageEngine, snippet_id: str
    ) -> None:
        for member in Language:
            result = await update_snippet(snippet_id, {"language": member.value}, storage)
            assert result["language"] == member.value
