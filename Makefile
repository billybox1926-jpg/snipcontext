.PHONY: lint test format mypy all build-binary build-wheel install-tool clean

lint:
	uv run ruff check src/snipcontext tests
	uv run ruff format --check src/snipcontext tests

format:
	uv run ruff format src/snipcontext tests
	uv run ruff check --fix src/snipcontext tests

test:
	uv run pytest tests -v

mypy:
	uv run mypy src/snipcontext --ignore-missing-imports --no-site-packages

all: lint mypy test

# ── Build ──────────────────────────────────────────────────────────

build-wheel:
	uv build

build-binary:
	uv run pyinstaller snipcontext.spec --clean --noconfirm

# Core-only binary (excludes semantic search, encryption, web, TUI)
build-binary-minimal:
	uv run pyinstaller snipcontext.spec --clean --noconfirm \
		--exclude-module sentence_transformers \
		--exclude-module faiss \
		--exclude-module cryptography \
		--exclude-module fastapi \
		--exclude-module uvicorn \
		--exclude-module prompt_toolkit

# ── Install as uv tool (lightweight — no venv management needed) ───

install-tool:
	uv tool install .

install-tool-all:
	uv tool install ".[all]"

uninstall-tool:
	uv tool uninstall snipcontext

# ── Clean ──────────────────────────────────────────────────────────

clean:
	rm -rf build/ dist/ *.egg-info/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
