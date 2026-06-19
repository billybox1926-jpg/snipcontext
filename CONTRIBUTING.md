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
