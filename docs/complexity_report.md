# Code Complexity & Maintainability Report

**Generated:** 2026-08-15 | **Tool:** radon + pygount | **Scope:** `src/snipcontext/`

## Summary

| Metric | Value |
|--------|-------|
| Total Python LOC (src, excl. web/static) | 6,922 |
| Python files analyzed | 61 |
| Files rated D or F (cyclomatic) | 4 |
| Files with MI < 20 (low maintainability) | 2 |

## Cyclomatic Complexity — Top 15 Most Complex Functions

| File | Function | Complexity | Rating |
|------|----------|------------|--------|
| core/analytics.py | compute_detailed_stats | 38 | E |
| cli/search.py | search | 30 | D |
| cli/stats.py | _render_detailed_stats | 29 | D |
| core/snippet_ops.py | edit_snippet | 26 | D |
| web/routers/web_ui.py | merge_tags | 15 | C |
| tui/formatter.py | format_output | 15 | C |
| core/importers.py | import_tar_gz | 15 | C |
| cli/git.py | git_pull | 15 | C |
| core/importers.py | parse_yaml_import | 13 | C |
| config/settings.py | get_config | 12 | C |
| core/index_backends.py | _create_backend | 11 | C |
| core/analytics.py | compute_basic_stats | 11 | C |
| core/importers.py | parse_json_import | 11 | C |
| cli/snippets.py | _print_snippet | 11 | C |
| cli/init.py | _init_git | 11 | C |

## Maintainability Index — Files Below 30 (Needs Attention)

| File | MI Score | Rating |
|------|----------|--------|
| tui/textual_app.py | 10.7 | C |
| core/index_backends.py | 18.2 | C |
| tui/commands.py | 23.0 | B |
| plugins/registry.py | 23.8 | B |
| core/search_fusion.py | 26.1 | B |

## Lines of Code by Directory

| Directory | LOC |
|-----------|-----|
| snipcontext/__init__.py | 2 |
| snipcontext/__main__.py | 21 |
| snipcontext/cli | 2,004 |
| snipcontext/config | 238 |
| snipcontext/core | 2,889 |
| snipcontext/plugins | 287 |
| snipcontext/providers | 415 |
| snipcontext/tui | 1,066 |
| **Total** | **6,922** |

## Remark

This report establishes the baseline for issue #169 (Code Complexity & Maintainability Assessment).
The highest cyclomatic complexity is in `cli/search.py::search` (C=30, rated D) and `cli/stats.py::_render_detailed_stats` (C=29, rated D).
Lowest maintainability index is in `core/search_fusion.py` (MI=26.07) and `core/index_backends.py` (MI=18.22, rated B).
These modules are candidates for refactoring in a future iteration.