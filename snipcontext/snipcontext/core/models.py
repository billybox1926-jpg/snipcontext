"""Core data models for SnipContext.

All SnipContext entities are defined as Pydantic v2 models for
robust validation, serialization, and type safety.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def _utc_now() -> datetime:
    """Return current UTC datetime."""
    return datetime.now(timezone.utc)


def _generate_id() -> str:
    """Generate a short unique identifier."""
    return str(uuid.uuid4())[:22]


class Language(str, Enum):
    """Common programming languages for syntax highlighting and filtering."""

    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    JSX = "jsx"
    TSX = "tsx"
    HTML = "html"
    CSS = "css"
    SCSS = "scss"
    JAVA = "java"
    KOTLIN = "kotlin"
    GO = "go"
    RUST = "rust"
    CPP = "cpp"
    C = "c"
    CSHARP = "csharp"
    PHP = "php"
    RUBY = "ruby"
    SWIFT = "swift"
    SQL = "sql"
    SHELL = "shell"
    BASH = "bash"
    POWERSHELL = "powershell"
    YAML = "yaml"
    JSON = "json"
    TOML = "toml"
    MARKDOWN = "markdown"
    DOCKERFILE = "dockerfile"
    TERRAFORM = "terraform"
    UNKNOWN = "unknown"


class SnippetVersion(BaseModel):
    """Represents a single version snapshot of a snippet.

    SnipContext uses immutable version snapshots. When a snippet is updated,
    a new version is created and the snippet's version history is preserved.
    """

    id: str = Field(default_factory=_generate_id)
    content: str = Field(..., min_length=1, description="The code content of this version")
    created_at: datetime = Field(default_factory=_utc_now)
    change_message: str = Field(default="", description="Description of what changed")
    change_hash: str = Field(
        default="",
        description="SHA-256 hash of content for integrity",
    )

    @model_validator(mode="after")
    def _compute_hash(self):
        """Auto-compute content hash if not provided."""
        if not self.change_hash and self.content:
            self.change_hash = hashlib.sha256(self.content.encode()).hexdigest()[:16]
        return self


class SnippetMetadata(BaseModel):
    """Rich metadata attached to every snippet.

    Supports extensible key-value pairs for custom use cases while
    providing first-class fields for common attributes.
    """

    model_config = ConfigDict(extra="allow")

    title: str = Field(..., min_length=1, max_length=200, description="Human-readable title")
    description: str = Field(default="", description="What this snippet does and when to use it")
    language: Language = Field(default=Language.UNKNOWN, description="Programming language")
    source_url: str = Field(default="", description="URL where this snippet originated")
    author: str = Field(default="", description="Original author or contributor")
    confidence: Literal["draft", "reviewed", "production", "reference"] = Field(
        default="draft",
        description="Quality level of this snippet",
    )
    llm_optimized: bool = Field(
        default=False,
        description="Whether this snippet has been refined for LLM consumption",
    )
    custom_tags: dict[str, Any] = Field(
        default_factory=dict,
        description="Extensible key-value metadata",
    )


class Snippet(BaseModel):
    """The central entity in SnipContext.

    A Snippet represents a reusable piece of code with rich metadata,
    versioning, and optional embedding vector for semantic search.
    """

    model_config = ConfigDict(validate_assignment=True)

    id: str = Field(default_factory=_generate_id, description="Unique snippet identifier")
    content: str = Field(..., min_length=1, description="Current code content")
    metadata: SnippetMetadata = Field(default_factory=lambda: SnippetMetadata(title="Untitled"))
    tags: list[str] = Field(default_factory=list, description="Searchable tags")
    versions: list[SnippetVersion] = Field(
        default_factory=list,
        description="Immutable version history",
    )
    embedding: list[float] | None = Field(
        default=None,
        description="Dense vector embedding for semantic search",
        exclude=True,  # Don't serialize to JSON - stored in vector index
    )
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)
    access_count: int = Field(default=0, description="Number of times snippet was retrieved")

    @field_validator("tags", mode="before")
    @classmethod
    def _normalize_tags(cls, v: list[str]) -> list[str]:
        """Normalize tags to lowercase, deduplicated, sorted."""
        if not v:
            return []
        cleaned = [t.strip().lower() for t in v if t.strip()]
        return sorted(set(cleaned))

    @property
    def content_hash(self) -> str:
        """Compute SHA-256 hash of current content."""
        return hashlib.sha256(self.content.encode()).hexdigest()[:16]

    @property
    def tag_line(self) -> str:
        """Return tags as a formatted string."""
        return ", ".join(f"#{t}" for t in self.tags)

    def bump_version(self, change_message: str = "") -> SnippetVersion:
        """Create a version snapshot from current state and append to history."""
        version = SnippetVersion(
            content=self.content,
            change_message=change_message or f"Auto-save at {_utc_now().isoformat()}",
        )
        self.versions.append(version)
        # Keep only last N versions to prevent unbounded growth
        max_versions = 50
        if len(self.versions) > max_versions:
            self.versions = self.versions[-max_versions:]
        return version

    def touch(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = _utc_now()

    def record_access(self) -> None:
        """Increment access counter."""
        self.access_count += 1

    def merge_tags(self, new_tags: list[str]) -> None:
        """Merge new tags into existing tag set."""
        combined = set(self.tags) | {t.strip().lower() for t in new_tags if t.strip()}
        self.tags = sorted(combined)

    def to_search_text(self) -> str:
        """Combine all searchable text fields into a single string."""
        parts = [
            self.metadata.title,
            self.metadata.description,
            self.content,
            " ".join(self.tags),
            self.metadata.language.value,
        ]
        return "\n".join(p for p in parts if p)


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------


class SearchMode(str, Enum):
    """Available search strategies."""

    SEMANTIC = "semantic"       # Dense vector similarity
    KEYWORD = "keyword"         # TF-IDF / BM25 style text search
    HYBRID = "hybrid"           # Weighted combination
    TAG = "tag"                 # Exact tag matching


class SearchResult(BaseModel):
    """A single result from a snippet search query."""

    model_config = ConfigDict(frozen=True)

    snippet: Snippet = Field(..., description="The matched snippet")
    score: float = Field(..., ge=0.0, le=1.0, description="Relevance score (1.0 = perfect match)")
    matched_by: Literal["semantic", "keyword", "hybrid", "tag"] = Field(
        ..., description="Which search strategy produced this match"
    )
    highlights: list[str] = Field(
        default_factory=list,
        description="Matched text fragments for display",
    )

    @property
    def id(self) -> str:
        """Convenience accessor for snippet ID."""
        return self.snippet.id
