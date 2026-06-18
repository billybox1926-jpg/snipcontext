# Architecture

This repository is a reusable template, so the architecture intentionally defines conventions without assuming a specific runtime, framework, product, or deployment target.

Use these folders as stable seams for future projects. Keep implementation code small, composable, and easy to replace.

For a tiny dependency-free walkthrough of the intended `core -> providers -> plugins` pattern, see `docs/examples/MODULAR_REFERENCE.md`.

## Layout

```text
core/
providers/
plugins/
config/
scripts/
tests/
docs/
```

## Folder responsibilities

### `core/`

Contains framework-independent domain logic. Code in `core/` should avoid direct network, file-system, database, UI, or vendor-specific calls when possible.

Good candidates:

- domain models
- pure transformations
- validation rules
- orchestration interfaces
- reusable service boundaries

### `providers/`

Contains adapters for external systems or runtime-specific integrations.

Good candidates:

- API clients
- database adapters
- file-system adapters
- cloud service adapters
- AI/model provider adapters

Providers should depend on `core/` contracts instead of forcing `core/` to know vendor details.

### `plugins/`

Contains optional extensions that can be added, removed, or replaced without rewriting core behavior.

Good candidates:

- feature modules
- command extensions
- workflow extensions
- experimental integrations

A plugin should declare what it needs and expose a small entry point. Avoid hidden global state.

### `config/`

Contains configuration defaults, schemas, examples, and environment documentation.

Good candidates:

- example config files
- schema files
- environment variable documentation
- validation helpers

Do not commit secrets. Prefer explicit placeholders such as `EXAMPLE_TOKEN` or `YOUR_API_KEY_HERE`.

### `scripts/`

Contains local development, maintenance, and automation helpers.

Scripts should be safe to run repeatedly, explain what they are doing, and avoid destructive behavior unless explicitly documented.

### `tests/`

Contains automated tests and fixtures.

Suggested organization:

- `tests/unit/` for isolated logic tests
- `tests/integration/` for adapter or provider tests
- `tests/fixtures/` for reusable sample data

## Dependency direction

Keep dependencies flowing inward:

```text
plugins -> providers -> core
scripts -> project tooling
config -> runtime setup
```

`core/` should not import from `providers/` or `plugins/`. This keeps the template portable and makes future rewrites less painful.

## Extension pattern

When adding a new capability:

1. Define the stable behavior in `core/`.
2. Put external-service details in `providers/`.
3. Put optional feature wiring in `plugins/`.
4. Document configuration in `config/`.
5. Add tests under `tests/`.

## Configuration pattern

Prefer configuration that is:

- explicit
- documented
- environment-aware
- safe by default
- easy to override in CI

Template repositories should use example files instead of real secrets or machine-specific paths.

## Portability rules

- Avoid hardcoded absolute paths.
- Keep OS-specific commands isolated in scripts.
- Prefer plain text docs and simple shell helpers.
- Keep provider-specific behavior outside `core/`.
- Make optional features removable without breaking the baseline template.
