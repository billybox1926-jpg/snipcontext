#!/usr/bin/env bash
# Bootstrap a SnipContext development environment.
#
# Creates a virtualenv, installs the project with its dev extra, and reports
# which optional extras are present. Safe to re-run: existing environments are
# reused rather than recreated.
#
# Usage:
#   bash scripts/bootstrap.sh            # core + dev tooling
#   bash scripts/bootstrap.sh --all      # also install every optional extra
#
# Referenced from CONTRIBUTING.md ("Local automation defaults").
set -euo pipefail

cd "$(dirname "$0")/.."

EXTRAS="dev"
if [ "${1:-}" = "--all" ]; then
  EXTRAS="dev,all"
  echo "==> Installing with every optional extra (semantic, tui, web, ollama, encryption)"
fi

# Prefer uv when available: it is what CI uses and it is dramatically faster.
if command -v uv >/dev/null 2>&1; then
  echo "==> Using uv"
  [ -d .venv ] || uv venv
  uv pip install -e ".[${EXTRAS}]"
  RUN="uv run"
else
  echo "==> uv not found; falling back to python -m venv + pip"
  PY="${PYTHON:-python3}"
  command -v "$PY" >/dev/null 2>&1 || PY=python
  [ -d .venv ] || "$PY" -m venv .venv

  if [ -x .venv/bin/python ]; then
    VENV_PY=.venv/bin/python          # POSIX
  else
    VENV_PY=.venv/Scripts/python.exe  # Windows
  fi

  "$VENV_PY" -m pip install --upgrade pip
  "$VENV_PY" -m pip install -e ".[${EXTRAS}]"
  RUN="$VENV_PY -m"
fi

echo
echo "==> Verifying the test suite can collect"
if [ "$RUN" = "uv run" ]; then
  uv run pytest --collect-only -q >/dev/null
else
  $RUN pytest --collect-only -q >/dev/null
fi
echo "    collection OK"

echo
echo "==> Optional extras present in this environment"
if [ "$RUN" = "uv run" ]; then
  uv run python - <<'PY'
import importlib.util as u
for mod, label in [
    ("sentence_transformers", "semantic search"),
    ("faiss", "vector index (faiss)"),
    ("fastapi", "web API"),
    ("textual", "TUI"),
    ("httpx", "ollama/web client"),
    ("cryptography", "encryption extra"),
]:
    print(f"    {'yes' if u.find_spec(mod) else 'no ':4s} {label}")
PY
fi

cat <<'EOS'

Bootstrap complete. Next steps:

  pytest                  run the test suite
  make lint               ruff check + format --check
  make mypy               type-check src/snipcontext
  make build-frontend     build the web UI (needs node >= 18, see .nvmrc)

Full guide: docs/developer-setup.md
EOS
