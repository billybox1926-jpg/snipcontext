# Contributing

Thanks for your interest in contributing.

## Ground rules

- Be respectful and follow our Code of Conduct.
- Prefer small, focused pull requests.
- Open an issue first for large or breaking changes.

## Development workflow

1. Fork and create a branch: `feature/short-description`
2. Make your changes with clear commit messages.
3. Run local validation (`format:check`, `lint`, `test`) before opening your PR.
4. Open a pull request using the PR template.

## Setting up for tests

The test suite requires the `[dev]` extra, which pulls in the pytest plugins
the suite depends on (`pytest-mock`, `pytest-snapshot`, `pytest-asyncio`, and
`hypothesis`). Without them pytest reports confusing "fixture not found"
errors or fails at collection.

With pip:

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest
```

With uv (faster):

```bash
uv venv
uv pip install -e ".[dev]"
uv run pytest
```

A clean install plus `pytest` should exit 0 (some tests skip when optional
extras like `semantic` or `web` are absent — that is expected). If collection
fails with a missing-plugin message, re-run the install command above; the
suite fails fast with the exact package names rather than a wall of red.

## Building the web UI

The frontend needs **node 18 or newer** (Vite 6's minimum). `.nvmrc` pins the
version this project develops against:

```bash
nvm use            # picks up .nvmrc
make build-frontend
```

`make build-frontend` runs a `check-node` prerequisite that fails with a clear
message if node is missing or too old, rather than surfacing an opaque
vite/esbuild error. `npm ci` installs exact package versions from
`package-lock.json`, so pinning node is what makes the build reproducible.

## Pull request checklist

- [ ] Scope is focused and understandable
- [ ] Tests or validation steps are included
- [ ] Docs are updated (if behavior changed)
- [ ] Changelog updated (if needed)

## Good first issues

If this is your first contribution to SnipContext, look for issues labeled:

- [`good first issue`](https://github.com/billybox1926-jpg/snipcontext/issues?q=is%3Aissue%20state%3Aopen%20label%3A%22good%20first%20issue%22) for small, well-scoped tasks.
- [`help wanted`](https://github.com/billybox1926-jpg/snipcontext/issues?q=is%3Aissue%20state%3Aopen%20label%3A%22help%20wanted%22) for tasks where community contributions are welcome.
- [`documentation`](https://github.com/billybox1926-jpg/snipcontext/issues?q=is%3Aissue%20state%3Aopen%20label%3Adocumentation) for README, examples, and docs improvements.

Good starter tasks are usually docs updates, small provider/export improvements, CLI help text, tests for existing behavior, or examples that make the project easier to use.

Before starting, leave a short comment on the issue describing the scope you plan to take. Keep the first PR small enough for maintainers to review quickly.

## Local automation defaults

- Bootstrap: `bash scripts/bootstrap.sh`
- Setup guide: `docs/developer-setup.md`
- CI workflows: `.github/workflows/`

## Release process

- SnipContext uses PyPI trusted publishing via GitHub Actions OIDC.
- Tag a release: `git tag vX.Y.Z && git push --tags`
- The publish workflow triggers automatically on tags matching `v*`.
- The workflow builds the package and publishes to PyPI without any API token.
- For testing, use a pre-release tag like `v0.1.0rc1` and publish to TestPyPI when needed.
- After release, bump the changelog if behavior changed.
