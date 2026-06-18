#!/usr/bin/env bash
set -euo pipefail

failures=0

report_failure() {
  echo "hygiene: $1" >&2
  failures=$((failures + 1))
}

check_required_files() {
  local required_files=(
    README.md
    LICENSE
    CONTRIBUTING.md
    SECURITY.md
    CODE_OF_CONDUCT.md
    CHANGELOG.md
    .editorconfig
    .gitattributes
    .gitignore
    docs/ARCHITECTURE.md
    docs/DEVEX.md
    docs/REPOSITORY_STANDARDS.md
    config/.env.example
  )

  for file in "${required_files[@]}"; do
    if [[ ! -f "$file" ]]; then
      report_failure "missing required file: $file"
    fi
  done
}

check_shell_syntax() {
  local script
  while IFS= read -r -d '' script; do
    bash -n "$script" || report_failure "shell syntax failed: $script"
  done < <(find . -type f -name '*.sh' -not -path './.git/*' -print0)
}

check_merge_markers() {
  local left middle right
  left="$(printf '<%.0s' {1..7})"
  middle="$(printf '=%.0s' {1..7})"
  right="$(printf '>%.0s' {1..7})"

  if git grep -n -e "$left" -e "$middle" -e "$right" -- . ':!.git' >/tmp/hygiene-markers.txt; then
    cat /tmp/hygiene-markers.txt >&2
    report_failure "possible unresolved merge markers found"
  fi
}

check_markdown_headings() {
  local file first_line
  while IFS= read -r -d '' file; do
    first_line="$(head -n 1 "$file")"
    if [[ "$first_line" != '#'* && "$first_line" != '---' ]]; then
      report_failure "markdown file should start with a heading or front matter: $file"
    fi
  done < <(find . -type f -name '*.md' -not -path './.git/*' -print0)
}

check_required_files
check_shell_syntax
check_merge_markers
check_markdown_headings

if [[ "$failures" -gt 0 ]]; then
  echo "Repository hygiene checks failed: $failures issue(s)." >&2
  exit 1
fi

echo "Repository hygiene checks passed."
