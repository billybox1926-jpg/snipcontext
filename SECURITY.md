# Security Policy

## Reporting a vulnerability

Please do **not** open public issues for security vulnerabilities.

Instead, report privately via [GitHub Security Advisories](https://github.com/billybox1926-jpg/snipcontext/security/advisories/new).

Include:
- A clear description of the issue
- Reproduction steps
- Affected versions/commits
- Potential impact

## Response timeline

SnipContext is maintained by a single maintainer, so these are good-faith
targets rather than guarantees:

| Stage | Target |
| --- | --- |
| Acknowledgement of your report | within 3 business days |
| Initial assessment (severity, in scope or not) | within 7 business days |
| Fix or documented mitigation for a confirmed issue | within 30 days |

If you have not heard back within 7 business days, please comment on the
advisory thread to bump it.

## Supported versions

| Version | Supported |
| --- | --- |
| Latest release on PyPI | Yes |
| Current `master` branch | Yes |
| Older releases | No — please upgrade |

Security fixes land on `master` and in the next PyPI release. There are no
long-term support branches.

## Scope

**In scope** — defects in SnipContext's own code:

- Snippet storage and the on-disk format (`core/storage.py`)
- Search and indexing (keyword, semantic, hybrid)
- The CLI, including argument and config handling
- The web API and web UI (`snipcontext/web/`)
- The export pipeline and provider formatters, including sanitization
  (code-fence breakout, terminal escape injection, Rich markup injection)
- Plugin loading and the entry-point discovery mechanism

**Out of scope:**

- Vulnerabilities in third-party dependencies, unless a SnipContext
  integration bug makes them exploitable in a way the dependency alone is
  not. Report those upstream first.
- Findings that require an attacker who already has local filesystem or
  shell access as the user running SnipContext. The snippet store is
  plain files owned by that user and is not a security boundary against
  local code execution.
- Running the web server (`snipcontext serve`) bound to a non-loopback
  interface. It defaults to `127.0.0.1` and ships no authentication, so
  exposing it to a network with `--host` is a deployment choice, not a
  product defect.
- Content you deliberately place in your own snippets.
- Missing hardening with no demonstrated impact, and automated scanner
  output without a working reproduction.

## Disclosure

Please give us a chance to ship a fix before publishing details. We will
coordinate timing with you on the advisory thread and credit you in the
release notes unless you prefer otherwise.
