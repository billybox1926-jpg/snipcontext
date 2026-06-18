# Repository Setup Notes

Some template quality depends on GitHub repository settings rather than committed files. Review these settings after creating a new repository from this template.

Keep this guidance generic. Project-specific rules can be stricter when needed.

## Default branch

Recommended default branch: `main`.

After the first stable setup pass, protect the default branch so all important changes flow through pull requests.

## Branch protection

Recommended default branch protection:

- require pull requests before merging
- require at least one approval before merging
- require status checks before merging
- require branches to be up to date before merging when practical
- block force pushes on protected branches
- block branch deletion on protected branches

For small solo projects, keep the rules lightweight enough that maintenance does not become painful. For shared projects, prefer stricter review and status-check rules.

## Required status checks

At minimum, require the main CI workflow once it is stable for the project.

Suggested required checks:

- repository hygiene
- format check, when configured
- lint, when configured
- tests, when configured

The template starts with generic hygiene checks. Downstream projects should enable stack-specific checks as soon as they choose a runtime or framework.

## Merge methods

Recommended defaults:

- **Squash merge** for small feature, docs, cleanup, and chore PRs
- **Merge commit** for larger work where preserving branch history helps review
- **Rebase merge** only when the team is comfortable with linear history and the PR does not need merge context

Keep allowed merge methods simple. If maintainers are unsure, allow squash and merge commits, then document the project preference in `CONTRIBUTING.md`.

## Auto-merge

Auto-merge is useful when:

- branch protection is configured
- required checks are reliable
- dependency or maintenance PRs are low risk
- the repository has clear review rules

Avoid auto-merge while the project is still defining its first CI checks or release process.

## Release workflow expectations

The release workflow is scaffolding. Before relying on it:

1. Confirm the project uses Semantic Versioning.
2. Confirm `CHANGELOG.md` expectations.
3. Decide whether releases are tag-only, notes-only, or artifact-producing.
4. Test the workflow manually before making it required.
5. Document any package publishing steps in project-specific docs.

## Practical setup order

1. Create the repository from the template.
2. Update project identity, contacts, and ownership files.
3. Configure CI commands for the project stack.
4. Confirm the hygiene workflow passes.
5. Enable branch protection and required checks.
6. Decide the default merge method.
7. Configure release automation when the project is ready to publish.
