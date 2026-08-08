# Importing snippets

SnipContext supports importing snippets from remote URLs, local files, archives, and built-in collections.
This makes it easier to share reusable code patterns across teams and bootstrap new projects.

## Supported sources

### Built-in collections

SnipContext includes curated built-in snippet sets that can be imported with the `snipcontext:` URI scheme.

```bash
sc import snipcontext:python-stdlib
```

Preview a built-in collection before importing:

```bash
sc import snipcontext:python-stdlib --dry-run
```

Available built-in collections:

- `python-stdlib`

## Supported formats

### YAML

```yaml
- title: "HTTP Client"
  content: |-
    import requests

    def fetch(url):
        return requests.get(url).text
  lang: python
  tags: [http, requests, python]
```

### JSON

```json
[
  {
    "title": "HTTP Client",
    "content": "import requests\n\ndef fetch(url):\n    return requests.get(url).text\n",
    "lang": "python",
    "tags": ["http", "requests", "python"]
  }
]
```

### Markdown

````markdown
---
title: "HTTP Client"
lang: python
tags:
  - http
  - requests
---

```python
import requests

def fetch(url):
    return requests.get(url).text
```
````

### Archive import (`.tar.gz`)

You can import from a gzipped tarball containing one or more snippet files.
The importer extracts supported files safely and then parses each file as YAML, JSON, or Markdown.

```bash
sc import https://example.com/snippets.tar.gz
```

## Preview mode

Use preview mode to inspect snippets before saving them into your collection.

```bash
sc import https://raw.githubusercontent.com/org/snippets/main/python.yaml --dry-run
```

Preview mode is also available for built-in collections:

```bash
sc import snipcontext:python-stdlib --dry-run
```

## Deduplication

SnipContext performs exact deduplication by content hash during import.
If an imported snippet already exists in the collection, it is skipped automatically.

## Search indexing

Imported snippets are refreshed in the search index automatically after import so they are immediately searchable.

If the search index does not yet exist, the importer rebuilds the index from all active snippets.

## Error handling

- URLs must use `https://` for remote imports.
- `file:///` URIs are rejected for security reasons.
- Built-in collection names must use the `snipcontext:<name>` scheme.
- YAML is parsed with `yaml.safe_load()` to prevent unsafe deserialization.
- Archive extraction prevents path traversal and rejects symbolic links.

## Examples

Import a remote YAML collection:

```bash
sc import https://raw.githubusercontent.com/org/snippets/main/python.yaml
```

Import built-in Python patterns:

```bash
sc import snipcontext:python-stdlib
```

Preview before importing:

```bash
sc import https://raw.githubusercontent.com/org/snippets/main/python.yaml --dry-run
```

Import a tarball of snippet files:

```bash
sc import https://github.com/org/snippets/archive/main.tar.gz
```
