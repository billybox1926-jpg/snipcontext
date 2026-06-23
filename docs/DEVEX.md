# Developer Experience Standards

This document defines lightweight DevEx conventions for repositories created from this template.

The goal is a low-friction contributor workflow that remains portable across languages, frameworks, and project sizes.

## Local workflow

Recommended contributor loop:

1. Read `README.md` for project purpose and layout.
2. Run `bash scripts/bootstrap.sh` to install or validate local prerequisites.
3. Copy `config/.env.example` to a local environment file if the project needs environment variables.
4. Make a focused change on a short-lived branch.
5. Run `bash scripts/validate.sh` before opening a pull request.
6. Open a PR with validation notes and any relevant screenshots or logs.

## Environment files

Keep examples safe and explicit:

- Commit `.env.example` files with placeholders only.
- Never commit real secrets, tokens, credentials, private keys, or local machine paths.
- Document required variables near the code or config that consumes them.
- Prefer clear placeholder values such as `YOUR_API_KEY_HERE` or `example.local`.

## Dependency management

Each project should document its package manager and lockfile policy.

Recommended defaults:

- Applications should commit lockfiles when the ecosystem supports them.
- Libraries and reusable templates may omit lockfiles unless reproducible installs require them.
- Keep runtime dependencies small and justified.
- Prefer standard tooling before adding extra packages.
- Update dependencies intentionally and include validation notes in PRs.

## Validation standards

Template repositories should support these task names when applicable:

- `format:check` for formatting validation
- `lint` for static analysis
- `test` for automated tests

Generic validation is always available through:

```bash
bash scripts/hygiene.sh
```

The hygiene check is stack-agnostic and currently verifies:

- required template files are present
- shell scripts parse successfully
- unresolved merge markers are not present
- Markdown files start with a top-level heading

`bash scripts/validate.sh` runs the generic hygiene checks first, then runs project-specific package commands when a supported project setup is present.

The reusable GitHub Actions workflow can call custom commands for each project. Local validation should stay simple and safe to run repeatedly.

## Debugging workflow

When something fails:

1. Reproduce the issue from a clean checkout if possible.
2. Capture the exact command, expected result, and actual result.
3. Check environment variables and local config against `config/.env.example`.
4. Run the smallest relevant validation command first.
5. Add notes to the issue or PR explaining what was verified.

Avoid committing temporary debug output, machine-specific paths, or local credentials.

## Error handling conventions

Prefer errors that are actionable:

- Say what failed.
- Say what input or config caused the failure when safe.
- Suggest the next command or config field to check.
- Avoid hiding errors with broad catch-all handling.
- Do not print secrets or sensitive values in logs.

## Coding standards

General coding expectations:

- Keep changes focused and easy to review.
- Favor clear names over clever abstractions.
- Keep core logic separate from provider or plugin code.
- Add tests for behavior, not implementation trivia.
- Update docs when behavior, setup, or architecture changes.
- Prefer small modules with obvious ownership.

## Pull request hygiene

A healthy PR should include:

- a clear summary
- linked issues when applicable
- validation steps
- screenshots or logs when useful

## Snapshot tests

We use `pytest-snapshot` to lock down CLI output and provider formatting.
Snapshot files live alongside the tests (for example, `tests/cli/snapshots/`).

To update snapshots after an intentional output change:

```bash
pytest tests/cli/test_cli_snapshots.py --snapshot-update
```

Review the diff before committing updated snapshots.

- documentation updates for user-facing or contributor-facing changes
