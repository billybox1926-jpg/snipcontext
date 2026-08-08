"""Built-in snippet collections for SnipContext.

These are shipped with the package and can be imported via the CLI using a
special source alias such as ``snipcontext:python-stdlib``.
"""

from __future__ import annotations

from typing import Final

import yaml

from snipcontext.core.importers import ImportedSnippet, parse_yaml_import

BUILTIN_COLLECTION_SCHEME: Final[str] = "snipcontext"

_BUILTIN_COLLECTIONS: dict[str, str] = {
    "python-stdlib": """
- title: "JSON Load"
  content: |-
    import json

    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
  lang: python
  tags: [json, python, stdlib]

- title: "Pathlib Read File"
  content: |-
    from pathlib import Path

    path = Path("data/input.txt")
    text = path.read_text(encoding="utf-8")
    print(text)
  lang: python
  tags: [pathlib, filesystem, python, stdlib]

- title: "HTTP Status Check"
  content: |-
    from urllib.request import urlopen

    with urlopen("https://example.com") as response:
        body = response.read().decode("utf-8")
        print(len(body))
  lang: python
  tags: [http, urllib, python, stdlib]

- title: "Temporary File"
  content: |-
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        print(tmpdir)
  lang: python
  tags: [tempfile, python, stdlib]
""",
}


def get_builtin_collection_names() -> list[str]:
    """Return sorted names of available built-in collections."""
    return sorted(_BUILTIN_COLLECTIONS)


def load_builtin_collection(name: str) -> list[ImportedSnippet]:
    """Load a built-in collection by name."""
    key = name.strip().lower().lstrip("/")
    if key not in _BUILTIN_COLLECTIONS:
        raise ValueError(f"Unknown built-in collection: {name}")
    return parse_yaml_import(_BUILTIN_COLLECTIONS[key])


def is_builtin_collection_source(url: str) -> bool:
    """Return True when the source URL is a built-in collection alias."""
    return url.startswith(f"{BUILTIN_COLLECTION_SCHEME}:")
