## Summary

Implements comprehensive error handling, resilience, and security features for SnipContext.

### 🔐 Encryption (Fernet/AES-128)
- Added `encrypted_content` field to Snippet model
- `EncryptionConfig` with PBKDF2 key derivation, auto-persisted salt
- `SNIPCONTEXT_ENCRYPT_ENABLED`, `SNIPCONTEXT_ENCRYPTION_PASSPHRASE`, `SNIPCONTEXT_ENCRYPT_KEY_SALT` env vars

### 🛡️ Index Resilience (Self-Healing)
- `VectorIndex.load()` / `KeywordIndex.load()` validate integrity (ID map length, matrix shape)
- Auto-cleanup of corrupted index files on load failure
- `HybridSearch.index_snippets()` auto-loads existing indices, rebuilds on corruption/missing
- New `HybridSearch.load_indices()` method returns `(semantic_loaded, keyword_loaded)`

### 🔁 Manual Index Rebuild CLI
- `sc rebuild-index --force` command with index existence check
- `--force` flag to force rebuild when index exists

### 🔐 Encryption CLI
- `sc encrypt <id>` - encrypt snippet content (clears plaintext)
- `sc decrypt <id>` - decrypt for viewing/editing
- `sc add --encrypt / --sensitive` flags

### ⚙️ Configuration
- `EncryptionConfig` with PBKDF2 (100k iterations default), auto-persisted salt
- `SNIPCONTEXT_ENCRYPT_ENABLED`, `SNIPCONTEXT_ENCRYPTION_PASSPHRASE`, `SNIPCONTEXT_ENCRYPT_KEY_SALT`

### 🛡️ Error Handling
- New typed exceptions: `IndexCorruptedError`, `MissingIndexError`, `EncryptionError`
- Auto-cleanup of corrupted index files on load failure
- Rich CLI error messages with actionable suggestions

### 🔄 Index Rebuild CLI
- `sc rebuild-index --force` with index existence check

### 🧪 Verification
- All 50 core tests pass
- Ruff lint: clean
- Mypy type check: clean
- Feature verified manually: encrypt/decrypt works end-to-end