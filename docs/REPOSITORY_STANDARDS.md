# Repository Standards

This document defines reusable standards for repository governance, naming, and release hygiene.

## Branch strategy

- Default branch: `main`
- Short-lived feature branches:
  - `feat/<short-description>`
  - `fix/<short-description>`
  - `chore/<short-description>`
  - `docs/<short-description>`

## Commit style

Recommended commit prefixes:

- `feat:` new functionality
- `fix:` bug fixes
- `docs:` documentation-only changes
- `chore:` maintenance and tooling
- `refactor:` internal improvements
- `test:` test additions/updates

## Pull request standards

- Keep changes focused and reviewable.
- Link related issue(s) in PR description.
- Include validation steps and expected outcomes.
- Update docs/changelog when behavior changes.

## Label taxonomy

Use a minimal, reusable label set:

- Type labels:
  - `type: bug`
  - `type: feature`
  - `type: docs`
  - `type: chore`
- Priority labels:
  - `priority: p0`
  - `priority: p1`
  - `priority: p2`
- Status labels:
  - `status: needs-triage`
  - `status: blocked`
  - `status: ready`

## Milestone strategy

Recommended milestone model:

- Time-based milestones (e.g., `2026-Q3`) for ongoing teams.
- Version-based milestones (e.g., `v1.4.0`) for release-driven projects.
- Keep milestone scope small enough for predictable closure.

## Release strategy

- Follow Semantic Versioning.
- Maintain `CHANGELOG.md` for notable changes.
- Tag releases with `vX.Y.Z`.

## Documentation standards

- Use clear headings (`#`, `##`, `###`) and concise sections.
- Prefer task-oriented instructions for onboarding.
- Keep placeholders explicit (`OWNER`, `REPO`, `security@example.com`).
