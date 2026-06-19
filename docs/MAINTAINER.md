# Maintainer Guide

This document is for project maintainers. It covers release procedures, CI/CD workflows, triage conventions, and the standards we enforce before anything ships.

## Release checklist

1. All CI checks green on `master`
2. `CHANGELOG.md` updated with user-facing changes since last tag
3. Version bumped in `pyproject.toml` (or confirmed correct from hatch)
4. `git tag vX.Y.Z && git push origin vX.Y.Z`
5. GitHub Release drafted from tag with changelog summary
6. CI `publish.yml` publishes to PyPI (trusted publishing, no tokens)
7. Verify `pip install snipcontext` resolves the new version

## CI pipeline

Three workflows:

- **`ci.yml`** — runs on every push/PR to `master`. Lint (ruff), type check (mypy), tests (pytest). All blocking.
- **`publish.yml`** — triggered on tag push. Builds and publishes to PyPI via OIDC.
- **`reusable-quality.yml`** — shared quality gates (importable by future workflows).

Lint and mypy are **blocking**. Documentation-only changes use `continue-on-error` on non-doc checks.

## Triage conventions

- New issues without the template → comment with template link, close if no response in 14 days
- `status: needs-triage` → assign within 1 week
- `status: blocked` → must reference the blocking issue/PR
- `good first issue` → keep 3-5 open at all times; prefer small, well-scoped tasks with clear acceptance criteria

## PR review standards

- One issue per commit (squash-merge preferred)
- PR description must link the issue it resolves (`Closes #N`)
- Tests required for new features and bug fixes
- Docs updated if user-facing behavior changes
- `CHANGELOG.md` entry for user-facing changes
- No force-push to feature branches (rebase locally if needed)

## Branch protection

- `master` is protected: PR + CI pass required
- Maintainers can bypass for docs-only or urgent fixes (use judgment)
- Delete merged feature branches

## Dependency policy

- Pin ranges in `pyproject.toml` (e.g., `>=1.0,<2.0`)
- Use `uv sync` to update `uv.lock`
- Review Dependabot PRs manually — verify changelog before merging
- Prefer fewer dependencies; new ones must justify their weight

## Communication

- GitHub Discussions for user questions and feature ideas (not Issues)
- Issues for bugs and concrete feature requests
- PRs for code discussion tied to a specific change
- Use draft PRs for work-in-progress; mark "Ready for review" when CI passes

## Acknowledging contributors

- When merging external PRs, leave a thank-you comment acknowledging the specific contribution
- Credit contributors in [CONTRIBUTORS.md](../CONTRIBUTORS.md)
- For significant contributions (new features, major docs), mention in the release notes
- Prefer squash-merge to keep history clean, but preserve co-author credit for substantial input:
  ```
  git commit --co-authored-by="Name <email@users.noreply.github.com>"
  ```
