.PHONY: lint test format mypy all

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
