.PHONY: lint test format mypy all maintenance check-node build-frontend build-binary build-wheel install-tool clean

lint:
	uv run ruff check src/snipcontext tests
	uv run ruff format --check src/snipcontext tests

format:
	uv run ruff format src/snipcontext tests
	uv run ruff check --fix src/snipcontext tests

test:
	uv run pytest tests -v

test-maintenance:
	uv run pytest -q -m "not slow" --cov=src/snipcontext --cov-report=term-missing --cov-fail-under=0

mypy:
	uv run mypy src/snipcontext --ignore-missing-imports --no-site-packages

maintenance: lint test-maintenance

all: lint mypy test

# ── Build ──────────────────────────────────────────────────────────

# Minimum node major version for the frontend build. Vite 6 requires node
# 18+; .nvmrc pins the version this project develops against (`nvm use`).
NODE_MIN_MAJOR := 18

# Verify the host node is new enough before running npm ci, so a too-old
# node fails with a clear message instead of an opaque vite/esbuild error.
check-node:
	@command -v node >/dev/null 2>&1 || { \
		echo "error: node not found on PATH. Install node $(NODE_MIN_MAJOR)+ (see .nvmrc)."; \
		exit 1; \
	}
	@major=$$(node -p 'process.versions.node.split(".")[0]'); \
	if [ "$$major" -lt "$(NODE_MIN_MAJOR)" ]; then \
		echo "error: node $$(node -v) is too old; need >= $(NODE_MIN_MAJOR) (see .nvmrc)."; \
		exit 1; \
	else \
		echo "node $$(node -v) OK (>= $(NODE_MIN_MAJOR))"; \
	fi

build-frontend: check-node
	cd web-ui && npm ci && npm run build
	mkdir -p src/snipcontext/web/static
	cp -R web-ui/dist/* src/snipcontext/web/static/

build-wheel: build-frontend
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
