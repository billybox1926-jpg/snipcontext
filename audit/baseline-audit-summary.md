# Issue #45 Phase 0 — Baseline Audit Summary

## Signature Gaps

### ClaudeProvider

- Missing methods: None
- Signature diffs:
  - `export_single`: was_abstract_now_concrete
  - `health_check`: was_abstract_now_concrete

### CursorProvider

- Missing methods: None
- Signature diffs:
  - `export_single`: was_abstract_now_concrete
  - `health_check`: was_abstract_now_concrete

### OpenAIProvider

- Missing methods: None
- Signature diffs:
  - `export_single`: was_abstract_now_concrete
  - `health_check`: was_abstract_now_concrete

### GenericProvider

- Missing methods: None
- Signature diffs:
  - `export_single`: was_abstract_now_concrete
  - `health_check`: was_abstract_now_concrete

## Behavior Gaps

> Network calls are patched for `requests`, `httpx`, and `openai` in this audit. Providers using unpatched libraries (e.g. `aiohttp`, `urllib3`, custom clients) may still touch the wire.

### ClaudeProvider

- Instantiable: True
- `export_single`: called
  - return type: str
  - expected return type: <class 'str'>
- `export_batch`: called
  - return type: str
  - expected return type: <class 'str'>
- `health_check`: called

### CursorProvider

- Instantiable: True
- `export_single`: called
  - return type: str
  - expected return type: <class 'str'>
- `export_batch`: called
  - return type: str
  - expected return type: <class 'str'>
- `health_check`: called

### OpenAIProvider

- Instantiable: True
- `export_single`: called
  - return type: str
  - expected return type: <class 'str'>
- `export_batch`: called
  - return type: str
  - expected return type: <class 'str'>
- `health_check`: called

### GenericProvider

- Instantiable: True
- `export_single`: called
  - return type: str
  - expected return type: <class 'str'>
- `export_batch`: called
  - return type: str
  - expected return type: <class 'str'>
- `health_check`: called

## Coverage Matrix

- CSV: C:\Users\Billy\Documents\GitHub\Snipcontext\audit\coverage-matrix.csv

## Notes

- mock_scope: requests, httpx, openai patched; other HTTP libs are not covered by this audit.

## Prioritised Fixes

