# Encryption at Rest

SnipContext supports encrypting snippet content at rest using **Fernet**
(symmetric encryption, AES‑128‑CBC + HMAC) with a key derived via
**PBKDF2‑HMAC‑SHA256**.

## When to Use Encryption

- Store sensitive code (credentials, tokens, personal data)
- Shared environments where the storage directory may be accessible to others
- Compliance requirements (e.g., GDPR, HIPAA) for data protection

## Requirements

- Python 3.10+ with the `[encryption]` extra installed:

  ```bash
  pip install snipcontext[encryption]
  ```

- The `cryptography` package is installed automatically with the extra.

> **Note on ARM / Termux:** The `cryptography` package requires Rust to build
> from source on platforms without pre-built wheels (ARM64, Android/Termux).
> On those platforms, install the core package only and avoid the `[encryption]`
> extra unless you have a Rust toolchain available.

## Key Derivation

| Parameter | Value |
|-----------|-------|
| Algorithm | PBKDF2‑HMAC‑SHA256 |
| Salt | Random 16‑byte value, stored in `config.yaml` as base64 |
| Key length | 32 bytes (Fernet requirement) |
| Iterations | 100,000 by default (configurable) |

The encryption key is **never written to disk** — it is derived on‑the‑fly
from your passphrase. Only the salt is persisted so the same key can be
re‑derived later.

## Configuration

Set these environment variables **before** enabling encryption:

| Variable | Default | Description |
|----------|---------|-------------|
| `SNIPCONTEXT_ENCRYPT_ENABLED` | `false` | Enable encryption globally |
| `SNIPCONTEXT_ENCRYPTION_PASSPHRASE` | *(none)* | **Required** — passphrase for key derivation |
| `SNIPCONTEXT_ENCRYPT_KEY_ITERATIONS` | `100000` | PBKDF2 iterations (minimum 10,000) |
| `SNIPCONTEXT_ENCRYPT_KEY_SALT` | *(auto)* | Base64‑encoded 16‑byte salt (auto‑generated if omitted) |

Example:

```bash
export SNIPCONTEXT_ENCRYPT_ENABLED=true
export SNIPCONTEXT_ENCRYPTION_PASSPHRASE="your-secure-passphrase"
```

After setting these, run SnipContext normally — encryption is applied
transparently when you use `--encrypt`.

## Usage

### Add an Encrypted Snippet

```bash
sc add "api_key = 'sk-12345'" \
  --title "API Key" \
  --tag secret \
  --encrypt
```

`--encrypt` stores the content encrypted; metadata (title, tags, language)
remains plaintext so snippets are still searchable.

### Mark a Snippet as Sensitive

```bash
sc add "DB_PASSWORD=secret123" \
  --title "DB Password" \
  --sensitive
```

`--sensitive` is a shorthand for `--encrypt`.

### Encrypt an Existing Snippet

```bash
sc encrypt <snippet-id>
```

Encrypts the content **in place** and clears the plaintext from storage.
The `encrypted_content` field is populated; `content` is set to empty.

### Decrypt a Snippet

```bash
sc decrypt <snippet-id>
```

Decrypts the content and restores it to the plaintext `content` field.
This **modifies** the stored snippet — use it when you need to edit or
view the original content.

### List / Search

`sc list` and `sc search` still show encrypted snippets, but their content
is replaced with `[encrypted]`. Metadata (title, tags, language) is
unchanged and fully searchable.

## Security Considerations

- **Passphrase strength:** Use a strong, unique passphrase. Encryption
  security depends on passphrase entropy, not the algorithm.
- **Key storage:** The key is **not stored anywhere** — it is derived
  from the passphrase each time. If you lose the passphrase, encrypted
  snippets cannot be recovered.
- **Salt:** Stored in `config.yaml` and is not a secret. Its purpose is
  to ensure the same passphrase produces a different key if you reinstall
  or share configs.
- **Iterations:** Increasing `SNIPCONTEXT_ENCRYPT_KEY_ITERATIONS` makes
  brute‑forcing slower but also slows encryption/decryption. On modern
  hardware, 100,000 iterations is a sensible default.
- **Backup your passphrase:** Store it in a password manager. Without it,
  encrypted snippets are unreadable.

## Threat Model

Encryption at rest protects against:

- Unauthorised disk access (e.g., exposed storage directory)
- Database/storage file exfiltration
- Physical device theft

It does **not** protect against:

- Memory scraping while SnipContext is running (the key is in memory)
- Keylogging or passphrase interception
- A compromised system where an attacker can run arbitrary commands

## Troubleshooting

- **`Encryption is not enabled`** — set `SNIPCONTEXT_ENCRYPT_ENABLED=true`
  and ensure the `[encryption]` extra is installed.
- **`SNIPCONTEXT_ENCRYPTION_PASSPHRASE env var must be set`** — export the
  passphrase before running SnipContext.
- **`decryption failed`** — usually means the wrong passphrase. Each
  passphrase maps to a different key derived from the stored salt.
- **Missing `cryptography` package** — reinstall with
  `pip install snipcontext[encryption]`.
