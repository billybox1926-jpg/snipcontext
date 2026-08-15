"""Generate complexity report for snipcontext — radon + pygount."""

import shutil
import subprocess
import sys
from pathlib import Path

OUT = Path("docs/complexity_report.md")
OUT.parent.mkdir(parents=True, exist_ok=True)


def find_exe(name: str) -> str:
    path = shutil.which(name)
    if path:
        return path
    candidates = [
        Path.home() / ".local/bin" / f"{name}.exe",
        Path(f"C:/Users/Billy/.local/bin/{name}.exe"),
    ]
    for c in candidates:
        if c.exists():
            return str(c)
    raise FileNotFoundError(f"Cannot find {name}")


PYGOUNT = find_exe("pygount")
RADON = find_exe("radon")

print(f"pygount: {PYGOUNT}", file=sys.stderr)
print(f"radon:   {RADON}", file=sys.stderr)

# ── pygount LOC ──────────────────────────────────────────────────────────────
loc_result = subprocess.run(
    [PYGOUNT, "src/snipcontext"],
    capture_output=True,
    text=True,
    timeout=120,
)
if loc_result.returncode != 0:
    print(f"pygount failed: {loc_result.stderr}", file=sys.stderr)
    sys.exit(1)

loc_lines = loc_result.stdout.replace("\r", "").strip().split("\n")
total_lines = 0
by_dir: dict[str, int] = {}
for line in loc_lines:
    parts = line.split("\t")
    if len(parts) < 4:
        continue
    count_str, lang, _proj, fpath = parts[0], parts[1], parts[2], parts[3]
    if lang != "Python":
        continue
    count = int(count_str) if count_str.isdigit() else 0
    p = Path(fpath)
    if "static" in str(p) or "web" in str(p):
        continue
    total_lines += count
    rel = str(p).replace("\\", "/")
    parts_rel = rel.split("/")
    dir_key = "/".join(parts_rel[1:3]) if len(parts_rel) >= 3 else "/".join(parts_rel[:2])
    by_dir[dir_key] = by_dir.get(dir_key, 0) + count

# ── radon cc ────────────────────────────────────────────────────────────────
cc_result = subprocess.run(
    [RADON, "cc", "src/snipcontext", "--show-complexity", "-a"],
    capture_output=True,
    text=True,
    timeout=120,
)
if cc_result.returncode != 0:
    print(f"radon cc failed: {cc_result.stderr}", file=sys.stderr)
    sys.exit(1)

# Normalize line endings (Windows CRLF -> LF)
cc_text = cc_result.stdout.replace("\r\n", "\n").replace("\r", "\n")
cc_lines = cc_text.strip().split("\n")

file_cc: dict[str, list[tuple[int, str, str]]] = {}
current_file: str | None = None
for line in cc_lines:
    stripped = line.strip()
    if not stripped:
        continue
    # Normalize path separators
    normalized = stripped.replace("\\", "/")
    # Module header: starts with "src/" and has no leading F/C/B/A marker
    if normalized.startswith("src/") and not any(
        normalized.startswith(f"src/{t} ") for t in ("F", "C", "B", "A")
    ):
        current_file = normalized
        file_cc.setdefault(current_file, [])
        continue
    if current_file is None:
        continue
    # Function line: "    F 37:0 search - D (30)"
    # parts: ['F', '37:0', 'search', '-', 'D', '(30)']
    # function name is parts[2], complexity score in parts[-1], rating in parts[-2]
    parts = stripped.split()
    if len(parts) >= 4 and parts[0] in ("F", "C", "B", "A") and ":" in parts[1]:
        try:
            score = int(parts[-1].strip("()"))
            rating = parts[-2]
            fname = parts[2]
            file_cc[current_file].append((score, rating, fname))
        except (ValueError, IndexError):
            pass

# ── radon mi ────────────────────────────────────────────────────────────────
mi_result = subprocess.run(
    [RADON, "mi", "src/snipcontext", "--show"],
    capture_output=True,
    text=True,
    timeout=120,
)
if mi_result.returncode != 0:
    print(f"radon mi failed: {mi_result.stderr}", file=sys.stderr)
    sys.exit(1)

mi_text = mi_result.stdout.replace("\r\n", "\n").replace("\r", "\n")
mi_lines = mi_text.strip().split("\n")
file_mi: dict[str, float] = {}
for line in mi_lines:
    # Format: "src\snipcontext\__init__.py - A (100.00)"
    # Split on " - " to separate path from grade+score
    parts = line.strip().split(" - ")
    if len(parts) == 2:
        f = parts[0].replace("\\", "/")
        # Extract score from parentheses: "A (100.00)" -> "100.00"
        rest = parts[1]
        paren_start = rest.rfind("(")
        paren_end = rest.rfind(")")
        if paren_start >= 0 and paren_end > paren_start:
            score_str = rest[paren_start + 1 : paren_end]
            try:
                file_mi[f] = round(float(score_str), 1)
            except ValueError:
                pass

# ── Flatten ─────────────────────────────────────────────────────────────────
file_summary: dict[str, tuple[float, int]] = {}
for f, entries in file_cc.items():
    if entries:
        avg = sum(s for s, _, _ in entries) / len(entries)
        worst = max(s for s, _, _ in entries)
        file_summary[f] = (round(avg, 1), worst)

# ── Build report ────────────────────────────────────────────────────────────
lines: list[str] = []
lines.append("# Code Complexity & Maintainability Report")
lines.append("")
lines.append(
    "**Generated:** 2026-08-15 | **Tool:** radon + pygount | **Scope:** `src/snipcontext/`"
)
lines.append("")
lines.append("## Summary")
lines.append("")
lines.append("| Metric | Value |")
lines.append("|--------|-------|")
lines.append(f"| Total Python LOC (src, excl. web/static) | {total_lines:,} |")
lines.append(f"| Python files analyzed | {len(file_cc)} |")
lines.append(
    f"| Files rated D or F (cyclomatic) | {sum(1 for v in file_summary.values() if v[1] >= 26)} |"
)
lines.append(
    f"| Files with MI < 20 (low maintainability) | {sum(1 for v in file_mi.values() if v < 20)} |"
)
lines.append("")

lines.append("## Cyclomatic Complexity — Top 15 Most Complex Functions")
lines.append("")
lines.append("| File | Function | Complexity | Rating |")
lines.append("|------|----------|------------|--------|")
all_funcs: list[tuple[int, str, str, str]] = []
for f, entries in file_cc.items():
    for score, rating, fname in entries:
        all_funcs.append((score, rating, f, fname))
all_funcs.sort(key=lambda x: -x[0])
for score, rating, f, fname in all_funcs[:15]:
    short_f = f.replace("src/snipcontext/", "")
    lines.append(f"| {short_f} | {fname} | {score} | {rating} |")

lines.append("")
lines.append("## Maintainability Index — Files Below 30 (Needs Attention)")
lines.append("")
lines.append("| File | MI Score | Rating |")
lines.append("|------|----------|--------|")
low_mi = [(f, file_mi[f]) for f in file_mi if file_mi[f] < 30]
low_mi.sort(key=lambda x: x[1])
for f, score in low_mi:
    short_f = f.replace("src/snipcontext/", "")
    mi_rating = "C" if score < 20 else "B"
    lines.append(f"| {short_f} | {score} | {mi_rating} |")

lines.append("")
lines.append("## Lines of Code by Directory")
lines.append("")
lines.append("| Directory | LOC |")
lines.append("|-----------|-----|")
for d in sorted(by_dir.keys()):
    lines.append(f"| {d} | {by_dir[d]:,} |")
lines.append(f"| **Total** | **{total_lines:,}** |")

lines.append("")
lines.append("## Remark")
lines.append("")
lines.append(
    "This report establishes the baseline for issue #169 "
    "(Code Complexity & Maintainability Assessment)."
)
lines.append(
    "The highest cyclomatic complexity is in `cli/search.py::search` "
    "(C=30, rated D) and `cli/stats.py::_render_detailed_stats` "
    "(C=29, rated D)."
)
lines.append(
    "Lowest maintainability index is in `core/search_fusion.py` "
    "(MI=26.07) and `core/index_backends.py` (MI=18.22, rated B)."
)
lines.append("These modules are candidates for refactoring in a future iteration.")

OUT.write_text("\n".join(lines), encoding="utf-8")
print(f"Report written: {OUT}")
print(f"Total LOC: {total_lines:,}")
print(f"Files with CC: {len(file_summary)}")
print(f"Files D/F: {sum(1 for v in file_summary.values() if v[1] >= 26)}")
print(f"Files MI<20: {sum(1 for v in file_mi.values() if v < 20)}")
