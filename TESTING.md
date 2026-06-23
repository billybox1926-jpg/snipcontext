# Testing Guide for SnipContext

This document outlines how to run the test suite, including the standard unit/E2E tests, the opt-in integration matrix, and property-based tests.

## Running the Standard Test Suite

To run the full test suite (excluding the slow integration matrix tests):

```bash
uv run pytest -q
```

This runs all tests marked as unit, E2E, and property-based. The integration matrix tests are skipped by default because they require the `SNIPCONTEXT_RUN_MODEL_MATRIX=1` flag and optionally available hardware (CUDA/MPS).

### With Coverage Report

To see a coverage report (enforces the 80% minimum for core code):

```bash
uv run pytest --cov=snipcontext --cov-report=term-missing
```

The build will fail if coverage drops below 80% for the `snipcontext` package (as configured in `pyproject.toml`).

## Running the Integration Matrix (Opt‑In)

The integration matrix tests real embedding models and devices (CPU, CUDA, MPS). They are marked as `slow` and `integration` and are opt‑in to avoid long runs in CI.

To run the matrix tests on CPU only (if you have `sentence-transformers` and `faiss-cpu` installed):

```bash
SNIPCONTEXT_RUN_MODEL_MATRIX=1 uv run pytest tests/integration/test_matrix.py -v -k "cpu"
```

To run the full matrix (including GPU/MPS if available):

```bash
SNIPCONTEXT_RUN_MODEL_MATRIX=1 uv run pytest tests/integration/test_matrix.py -v
```

> **Note**: The matrix tests will skip any device that is not available on the current machine.

## Property‑Based Tests (Hypothesis)

Property‑based tests live under `tests/property/` and use Hypothesis to generate random inputs and assert invariants. They are fast and run as part of the default test suite.

To run only the property‑based tests:

```bash
uv run pytest tests/property/ -v
```

## Test Categories and Markers

- `unit`: Standard unit tests (default).
- `integration`: Slow integration tests (matrix).
- `property`: Property‑based tests using Hypothesis.
- `slow`: Tests that take a noticeable amount of time (includes integration).
- `e2e`: End‑to‑end CLI tests (in `tests/cli/test_e2e.py`).

You can combine markers, e.g.:

```bash
uv run pytest -m "not slow" -q   # run everything except slow tests
```

## Writing New Tests

### Unit / E2E Tests

- Place new unit tests in `tests/<domain/>`.

- For CLI end‑to‑end tests, add to `tests/cli/test_e2e.py` or a new file under `tests/cli/`.

- Use the `temp_dir` fixture for isolated storage and the `mock_embeddings` fixture to avoid downloading real models.

### Property‑Based Tests

- Use `@given` strategies from `hypothesis`.

- Reuse existing strategies in `tests/property/test_hybrid_properties.py` and `tests/property/test_provider_schema.py` if applicable.

- Keep examples small (`max_examples=25` or lower) to keep the test suite fast.

### Integration Matrix

- Add new model/device combinations to `tests/integration/test_matrix.py`.

- Guard heavy imports with `pytest.importorskip` and skip if dependencies are missing.

- Use the `temp_dir` fixture for isolated storage.

## Provider Format Contract

All providers (`snipcontext.providers.*`) implement:

- `export_single(snippet: Snippet) -> str`
- `export_batch(snippets: list[Snippet], title: str = "Code Context") -> str`

The return value is a plain text string formatted for the target LLM or IDE. Providers **must not** raise exceptions for any valid `Snippet` input (including empty content, unusual Unicode, etc.). Tests should verify that the output is a non‑empty string and, for structured formats, perform light schema validation (see `tests/property/test_provider_schema.py`).

## Plugin Test Pattern

Plugins are discovered via entry points. To test plugin loading and discovery:

- Use the `temp_entry_points` fixture from `tests/conftest.py` to register fake entry points.

- Use the `fake_plugin_factory` fixture to create a mock `Plugin` subclass with a `PluginManifest`.

- Assert that `PluginRegistry.discover()` returns the expected count and that the plugin appears in `list_providers()` or `list_plugins()`.

See `tests/property/test_provider_schema.py` for an example.

## Benchmark Tests

Benchmark tests for vector index latency are marked `slow` and are excluded from the default test run. Run them with:

```bash
uv run pytest -q -m "slow"
```

Or run just the benchmark smoke tests:

```bash
uv run pytest tests/cli/test_benchmark.py -q
```

## Continuous Integration

The CI pipeline runs:

1. `uv run pytest -q -m "not slow"` (standard suite, coverage enforced at 68%).
2. `uv run pytest -q -m "slow"` (benchmarks, on push to main / manual dispatch).
3. A separate `test-semantic` job installs `faiss-cpu` and `sentence-transformers` to exercise the backend-specific code paths.

## Troubleshooting

- **Missing Semantic Dependencies**: If you see `Semantic search dependencies are not installed`, install with `uv pip install -e .[semantic]`.
- **Hypothesis Too Slow**: Adjust `max_examples` or use `@settings(suppress_health_check=[HealthCheck.too_slow])`.
- **Coverage Drop**: Ensure new lines are covered by unit tests; the CI will fail if coverage < 80%.
