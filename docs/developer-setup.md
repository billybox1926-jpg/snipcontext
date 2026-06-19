# Developer Setup

This guide provides generic onboarding defaults intended for template-based repositories.

For broader contributor workflow, dependency, debugging, validation, and coding standards, see `docs/DEVEX.md`.

## 1) Prerequisites

- Git 2.40+
- Bash or another POSIX-compatible shell for helper scripts
- A language runtime/toolchain for your project such as Node, Python, Go, Rust, or similar
- A package manager such as npm, pnpm, pip, poetry, go, or cargo

## 2) Bootstrap locally

```bash
git clone <your-repo-url>
cd <your-repo>
bash scripts/bootstrap.sh
```

If your repository is not Node.js based, adapt `scripts/bootstrap.sh` to your stack and keep command names consistent with CI.

If the project needs runtime configuration, copy `config/.env.example` to your local environment file and replace placeholder values locally.

## 3) Recommended task contract

To keep automation portable, define task commands with predictable names:

- `format:check` — formatting validation
- `lint` — static analysis/linting
- `test` — automated tests

This template's reusable workflow can call any shell command, but these names improve discoverability.

## 4) Local validation

Run the reusable validation helper before opening a PR:

```bash
bash scripts/validate.sh
```

Adapt this script as the project adopts a specific language stack.

## 5) CI customization

The repository ships with:

- `.github/workflows/reusable-quality.yml` as the reusable workflow
- `.github/workflows/ci.yml` as the default entry workflow
- `.github/workflows/release.yml` for release PR and tag automation

In `ci.yml`, enable checks by setting:

- `setup-node: true` for JS/TS projects
- `run-format-check: true`
- `run-lint: true`
- `run-test: true`

Then optionally override commands:

```yaml
with:
  setup-node: true
  format-command: npm run format:check
  lint-command: npm run lint
  test-command: npm test
```

## 6) Branch and PR workflow

1. Create a branch from `main`.
2. Run local validation commands before opening a PR.
3. Open a focused PR and include context for reviewers.
4. Merge only when CI checks pass.

## 7) Lightweight automation standards

- Keep workflows minimal and composable.
- Prefer reusable workflows over duplicated YAML.
- Avoid stack-specific assumptions in template defaults.
- Keep commands configurable through workflow inputs.
- Fail fast in CI and keep logs clear.
