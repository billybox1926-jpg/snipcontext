#!/usr/bin/env bash
set -euo pipefail

bash scripts/hygiene.sh

if [[ -f package.json ]]; then
  if command -v npm >/dev/null 2>&1; then
    npm run format:check --if-present
    npm run lint --if-present
    npm test --if-present
  else
    echo "npm is not installed; skipping Node validation."
  fi
else
  echo "No package.json found; add project-specific validation commands here as the template is adopted."
fi

echo "Validation complete."
