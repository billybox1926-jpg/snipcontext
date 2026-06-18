# OSS Repository Template

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Contributions Welcome](https://img.shields.io/badge/contributions-welcome-brightgreen.svg)](CONTRIBUTING.md)
[![Security Policy](https://img.shields.io/badge/security-policy-blue.svg)](SECURITY.md)

A reusable, professional baseline for open source repositories.

Use this template when you want clean OSS defaults, modular architecture conventions, reusable DevEx, and lightweight automation without locking a new project to one language or framework.

## What is included

- Repository health files: `LICENSE`, `CONTRIBUTING.md`, `SECURITY.md`, and `CODE_OF_CONDUCT.md`
- GitHub collaboration scaffolding: issue templates, pull request template, and `CODEOWNERS`
- Modular project structure: `core/`, `providers/`, `plugins/`, `config/`, `scripts/`, and `tests/`
- Reusable documentation for standards, architecture, DevEx, setup, and repository settings
- Baseline repository config: `.editorconfig`, `.gitattributes`, and `.gitignore`
- Generic CI, release, bootstrap, validation, and hygiene automation

## Quick start

1. Click **Use this template** on GitHub.
2. Rename the repository and update project-specific fields.
3. Review the documentation map below.
4. Confirm or replace `LICENSE` for your legal requirements.
5. Update contacts in `SECURITY.md`, `CODEOWNERS`, and template placeholders.
6. Copy `config/.env.example` if runtime configuration is needed.
7. Review `docs/REPOSITORY_SETUP.md`, then enable branch protection and required status checks.

## Documentation map

| Need | Start here |
| --- | --- |
| Local setup and CI customization | `docs/developer-setup.md` |
| Developer workflow, validation, debugging, and coding standards | `docs/DEVEX.md` |
| Modular architecture conventions | `docs/ARCHITECTURE.md` |
| Concrete `core -> providers -> plugins` walkthrough | `docs/examples/MODULAR_REFERENCE.md` |
| Branch, commit, label, milestone, and release standards | `docs/REPOSITORY_STANDARDS.md` |
| GitHub repository settings, branch protection, and merge/release setup | `docs/REPOSITORY_SETUP.md` |
| Contribution expectations | `CONTRIBUTING.md` |
| Security reporting | `SECURITY.md` |

## Repository layout

```text
.github/
  ISSUE_TEMPLATE/
  workflows/
  PULL_REQUEST_TEMPLATE.md
  CODEOWNERS
core/
providers/
plugins/
config/
  .env.example
docs/
  ARCHITECTURE.md
  DEVEX.md
  REPOSITORY_SETUP.md
  REPOSITORY_STANDARDS.md
  developer-setup.md
  examples/
    MODULAR_REFERENCE.md
scripts/
  bootstrap.sh
  hygiene.sh
  validate.sh
tests/
CHANGELOG.md
CODE_OF_CONDUCT.md
CONTRIBUTING.md
LICENSE
SECURITY.md
```

## Automation

- `.github/workflows/ci.yml` runs the reusable quality workflow.
- `.github/workflows/reusable-quality.yml` provides configurable hygiene, format, lint, and test checks.
- `.github/workflows/release.yml` provides release automation scaffolding.
- `bash scripts/bootstrap.sh` supports local setup.
- `bash scripts/hygiene.sh` runs stack-agnostic repository checks.
- `bash scripts/validate.sh` runs hygiene first, then project-specific checks when configured.

## Repository settings

Recommended GitHub settings are documented in `docs/REPOSITORY_SETUP.md`.

At minimum, review:

- default branch protection
- required status checks
- allowed merge methods
- release workflow expectations

## Versioning and releases

Use [Semantic Versioning](https://semver.org/) and keep a human-readable `CHANGELOG.md`.

- **MAJOR**: incompatible API or behavior changes.
- **MINOR**: backward-compatible functionality.
- **PATCH**: backward-compatible fixes.

## Suggested next steps

- Enable or customize the workflow commands for your stack.
- Fill the modular folders with project-specific implementation code.
- Add project-specific architecture and operations notes under `docs/`.
- Configure release automation if you publish artifacts.
