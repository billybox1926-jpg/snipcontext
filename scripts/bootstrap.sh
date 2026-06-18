#!/usr/bin/env bash
set -euo pipefail

if [[ ! -f package.json ]]; then
  echo "No package.json found. This bootstrap script is currently oriented to Node.js projects."
  echo "Copy and adapt scripts/bootstrap.sh for your stack (Python, Go, Rust, etc.)."
  exit 0
fi

if command -v npm >/dev/null 2>&1; then
  npm ci
  echo "Dependencies installed."
else
  echo "npm is not installed. Please install Node.js 20+ and retry."
  exit 1
fi
