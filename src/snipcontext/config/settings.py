"""Configuration management for SnipContext.

Uses Pydantic Settings for env-var aware configuration with sensible
defaults and platform-appropriate directory resolution.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from platformdirs import user_config_dir, user_data_dir
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_APP_NAME = "SnipContext"
_APP_AUTHOR = "snipcontext"


class EmbeddingConfig(BaseSettings):
    """Configuration for the local embedding model."""

    model_config = SettingsConfigDict(env_prefix="SNIPCONTEXT_EMBED_", extra="ignore")

    model_name: str = Field(
        default="all-MiniLM-L6-v2",
        description="Sentence-transformers model for embeddings",
    )
    device: Literal["cpu", "cuda", "mps"] = Field(default="cpu")
    normalize: bool = Field(default=True, description="L2-normalize embedding vectors")
    batch_size: int = Field(default=32, ge=1)
    query_instruction: str = Field(
        default="query: ",
        description="Prefix for query text (model-specific)",
    )
    doc_instruction: str = Field(
        default="",
        description="Prefix for document text (model-specific)",
    )


class SearchConfig(BaseSettings):
    """Configuration for search behavior."""

    model_config = SettingsConfigDict(env_prefix="SNIPCONTEXT_SEARCH_", extra="ignore")

    default_mode: Literal["semantic", "keyword", "hybrid", "tag"] = Field(default="hybrid")
    semantic_weight: float = Field(default=0.7, ge=0.0, le=1.0)
    keyword_weight: float = Field(default=0.3, ge=0.0, le=1.0)
    top_k: int = Field(default=10, ge=1, le=100)
    min_score: float = Field(default=0.1, ge=0.0, le=1.0)
    rerank: bool = Field(default=True)


class StorageConfig(BaseSettings):
    """Configuration for local storage backend."""

    model_config = SettingsConfigDict(env_prefix="SNIPCONTEXT_STORAGE_", extra="ignore")

    data_dir: Path = Field(
        default_factory=lambda: Path(user_data_dir(_APP_NAME, _APP_AUTHOR)),
    )
    snippets_dir: str = Field(default="snippets")
    index_dir: str = Field(default="index")
    auto_commit: bool = Field(
        default=True,
        description="Auto-stage changes for git tracking",
    )
    pretty_json: bool = Field(default=True)
    json_indent: int = Field(default=2)
    max_file_size_mb: int = Field(default=10, ge=1, le=100)
    watchdog_enabled: bool = Field(default=True, description="Enable filesystem watcher auto-index")
    watchdog_poll_interval: float = Field(
        default=5.0, ge=0.1, description="Watcher poll interval seconds"
    )


class ExportConfig(BaseSettings):
    """Configuration for LLM export formats."""

    model_config = SettingsConfigDict(env_prefix="SNIPCONTEXT_EXPORT_", extra="ignore")

    default_provider: str = Field(default="generic")
    include_metadata: bool = Field(default=True)
    wrap_code_blocks: bool = Field(default=True)
    max_snippets_per_export: int = Field(default=50, ge=1)
    include_line_numbers: bool = Field(default=False)


class EncryptionConfig(BaseSettings):
    """Configuration for snippet encryption (Fernet/AES-128)."""

    model_config = SettingsConfigDict(env_prefix="SNIPCONTEXT_ENCRYPT_", extra="ignore")

    enabled: bool = Field(default=False, description="Enable snippet encryption")
    key_iterations: int = Field(
        default=100000, ge=10000, description="PBKDF2 iterations for key derivation"
    )
    key_salt: str | None = Field(
        default=None,
        description="Base64-encoded salt for key derivation (auto-generated if not provided)",
    )

    def get_or_create_salt(self) -> bytes:
        """Get existing salt or generate and persist a new one."""
        if self.key_salt:
            import base64

            return base64.b64decode(self.key_salt)

        import base64
        import secrets

        salt = secrets.token_bytes(16)
        # Auto-save the salt to config
        self.key_salt = base64.b64encode(salt).decode()
        # Persist to config file
        try:
            from snipcontext.config.settings import get_config

            config = get_config()
            config.encryption.key_salt = self.key_salt
            config.save_to_file()
        except Exception:
            pass  # Best effort to persist salt

        return salt


class AutoTagConfig(BaseSettings):
    """Configuration for auto-tag suggestions."""

    model_config = SettingsConfigDict(env_prefix="SC_AUTO_TAG_", extra="ignore")

    enabled: bool = Field(
        default=True,
        description="Enable local auto-tag suggestions from the FAISS index",
    )
    top_k: int = Field(default=5, ge=1, le=50)
    min_frequency: int = Field(default=2, ge=1)
    auto_accept: bool = Field(
        default=False,
        description="Apply suggestions automatically without interactive prompt",
    )


class Config(BaseSettings):
    """Root configuration for SnipContext.

    All settings can be overridden via environment variables using
    the SNIPCONTEXT_ prefix, or via a config file at the platform-appropriate
    configuration directory.
    """

    model_config = SettingsConfigDict(
        env_prefix="SNIPCONTEXT_",
        env_nested_delimiter="__",
        extra="ignore",
    )

    debug: bool = Field(default=False)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(default="INFO")

    embedding: EmbeddingConfig = Field(default_factory=EmbeddingConfig)
    search: SearchConfig = Field(default_factory=SearchConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    export: ExportConfig = Field(default_factory=ExportConfig)
    auto_tag: AutoTagConfig = Field(default_factory=AutoTagConfig)
    dedup: DedupConfig = Field(default_factory=DedupConfig)
    encryption: EncryptionConfig = Field(default_factory=EncryptionConfig)
    auto_tag: AutoTagConfig = Field(default_factory=AutoTagConfig)

    @field_validator("storage", mode="before")
    @classmethod
    def _resolve_storage_paths(cls, v):
        """Ensure storage paths are absolute and resolved."""
        if isinstance(v, dict):
            data_dir = Path(v.get("data_dir", user_data_dir(_APP_NAME, _APP_AUTHOR)))
            if not data_dir.is_absolute():
                data_dir = Path.home() / data_dir
            v["data_dir"] = data_dir.expanduser().resolve()
        return v

    @property
    def snippets_path(self) -> Path:
        """Resolved path to the snippets storage directory."""
        return self.storage.data_dir / self.storage.snippets_dir

    @property
    def index_path(self) -> Path:
        """Resolved path to the search index directory."""
        return self.storage.data_dir / self.storage.index_dir

    @property
    def config_file_path(self) -> Path:
        """Path to the user configuration file."""
        return Path(user_config_dir(_APP_NAME, _APP_AUTHOR)) / "snipcontext.yaml"

    def ensure_directories(self) -> None:
        """Create all required directories if they don't exist."""
        self.snippets_path.mkdir(parents=True, exist_ok=True)
        self.index_path.mkdir(parents=True, exist_ok=True)

    def save_to_file(self) -> None:
        """Persist current configuration to YAML file."""
        import yaml

        self.config_file_path.parent.mkdir(parents=True, exist_ok=True)
        payload = self.model_dump(mode="json", exclude_none=True)
        with open(self.config_file_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(payload, f, default_flow_style=False, sort_keys=False)


@lru_cache(maxsize=1)
def get_config() -> Config:
    """Get the singleton Config instance.

    Cached so that configuration is loaded once per process.
    """
    return Config()


def reset_config() -> None:
    """Clear the config cache (useful for testing)."""
    get_config.cache_clear()
