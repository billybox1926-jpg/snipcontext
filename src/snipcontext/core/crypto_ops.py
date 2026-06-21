"""Crypto domain business logic.

Pure functions for encryption/decryption operations.
No I/O, no CLI dependencies.
"""

from __future__ import annotations

from snipcontext.config.settings import Config
from snipcontext.core.storage import StorageError


def encrypt_content(config: Config, storage: "StorageEngine", content: str) -> str:
    """Encrypt content using the configured encryption settings.

    Args:
        config: Application config (must have encryption enabled).
        storage: Storage engine instance.
        content: Plaintext content to encrypt.

    Returns:
        Base64-encoded encrypted string.

    Raises:
        StorageError: If encryption is not enabled or fails.
    """
    if not config.encryption.enabled:
        raise StorageError(
            "encrypt",
            original_error=RuntimeError(
                "Encryption is not enabled. Set SNIPCONTEXT_ENCRYPT_ENABLED=true"
            ),
        )
    return storage.encrypt_content(content)


def decrypt_content(config: Config, storage: "StorageEngine", encrypted_content: str) -> str:
    """Decrypt content using the configured encryption settings.

    Args:
        config: Application config (must have encryption enabled).
        storage: Storage engine instance.
        encrypted_content: Base64-encoded encrypted string.

    Returns:
        Decrypted plaintext content.

    Raises:
        StorageError: If encryption is not enabled or decryption fails.
    """
    if not config.encryption.enabled:
        raise StorageError(
            "decrypt",
            original_error=RuntimeError(
                "Encryption is not enabled. Set SNIPCONTEXT_ENCRYPT_ENABLED=true"
            ),
        )
    return storage.decrypt_content(encrypted_content)
