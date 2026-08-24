"""Assignment-validation tests for SnippetMetadata (issue #201).

``SnippetMetadata`` set ``ConfigDict(extra="allow")`` without
``validate_assignment=True`` (only ``Snippet`` had it). Assigning an invalid
value therefore silently stored the raw value, which then persisted to disk
and made every subsequent load of that snippet raise ``ValidationError`` — a
corrupted record the tool could no longer open, strictly worse than a
rejected write.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from snipcontext.config.settings import Config, StorageConfig
from snipcontext.core.models import Language, Snippet, SnippetMetadata
from snipcontext.core.storage import StorageEngine


class TestMetadataAssignmentValidation:
    """Invalid in-place assignments must raise instead of being stored."""

    def test_invalid_language_string_raises(self) -> None:
        metadata = SnippetMetadata(title="t")
        with pytest.raises(ValidationError):
            metadata.language = "not-a-language"

    def test_invalid_language_leaves_field_unchanged(self) -> None:
        metadata = SnippetMetadata(title="t", language=Language.PYTHON)
        with pytest.raises(ValidationError):
            metadata.language = "not-a-language"
        assert metadata.language is Language.PYTHON

    @pytest.mark.parametrize(
        ("field", "value"),
        [
            ("language", "not-a-language"),
            ("confidence", "bogus"),
            ("title", ""),
            ("title", "x" * 201),
            ("custom_tags", "not-a-dict"),
        ],
    )
    def test_constrained_fields_reject_bad_values(self, field: str, value: object) -> None:
        metadata = SnippetMetadata(title="t")
        with pytest.raises(ValidationError):
            setattr(metadata, field, value)


class TestMetadataAssignmentStillWorks:
    """Valid assignments keep working, and strings coerce to the enum."""

    def test_valid_language_string_coerces_to_enum(self) -> None:
        metadata = SnippetMetadata(title="t")
        metadata.language = "rust"
        assert metadata.language is Language.RUST

    def test_valid_enum_member_accepted(self) -> None:
        metadata = SnippetMetadata(title="t")
        metadata.language = Language.PYTHON
        assert metadata.language is Language.PYTHON

    def test_plain_string_fields_accepted(self) -> None:
        metadata = SnippetMetadata(title="t")
        metadata.description = "what it does"
        metadata.source_url = "https://example.com"
        metadata.framework = "fastapi"
        metadata.version = "0.100+"
        metadata.author = "Dev"
        assert metadata.framework == "fastapi"

    def test_confidence_and_flags_accepted(self) -> None:
        metadata = SnippetMetadata(title="t")
        metadata.confidence = "production"
        metadata.llm_optimized = True
        metadata.custom_tags = {"k": "v"}
        assert metadata.confidence == "production"

    def test_extra_allow_still_permits_unknown_attributes(self) -> None:
        """validate_assignment must not break the extra="allow" contract."""
        metadata = SnippetMetadata(title="t")
        metadata.some_custom_field = "anything"
        assert metadata.some_custom_field == "anything"


class TestMetadataRoundtrip:
    """Saving and reloading must preserve a valid Language member."""

    @pytest.fixture
    def storage(self, tmp_path: Path) -> StorageEngine:
        config = Config(
            storage=StorageConfig(
                data_dir=tmp_path,
                snippets_dir="snippets",
                index_dir="index",
            )
        )
        return StorageEngine(config)

    def test_valid_language_survives_save_and_load(self, storage: StorageEngine) -> None:
        snippet = Snippet(
            content="fn main() {}",
            metadata=SnippetMetadata(title="Roundtrip", language=Language.RUST),
            tags=["rust"],
        )
        storage.save(snippet)

        loaded = storage.get(snippet.id)
        assert loaded.metadata.language is Language.RUST

    def test_assignment_then_save_roundtrips(self, storage: StorageEngine) -> None:
        """A coerced assignment persists as the enum value, not a raw str."""
        snippet = Snippet(
            content="x = 1",
            metadata=SnippetMetadata(title="Coerce", language=Language.PYTHON),
            tags=[],
        )
        storage.save(snippet)

        loaded = storage.get(snippet.id)
        loaded.metadata.language = "rust"
        storage.save(loaded)

        assert storage.get(snippet.id).metadata.language is Language.RUST

    def test_rejected_assignment_cannot_corrupt_stored_snippet(
        self, storage: StorageEngine
    ) -> None:
        """The corruption path from #201: bad value written, snippet unopenable."""
        snippet = Snippet(
            content="x = 1",
            metadata=SnippetMetadata(title="Corrupt", language=Language.PYTHON),
            tags=[],
        )
        storage.save(snippet)

        loaded = storage.get(snippet.id)
        with pytest.raises(ValidationError):
            loaded.metadata.language = "not-a-language"
        storage.save(loaded)

        # Would raise ValidationError on the old behaviour.
        reloaded = storage.get(snippet.id)
        assert reloaded.metadata.language is Language.PYTHON
