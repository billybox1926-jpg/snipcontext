"""SnipContext — AI-powered code snippet & context manager."""

__version__ = "0.1.0"
__all__ = [
    "Snippet",
    "SnippetMetadata",
    "SnippetVersion",
    "SearchResult",
    "SearchMode",
    "StorageEngine",
    "SemanticSearch",
    "HybridSearch",
    "Config",
]

from snipcontext.core.models import Snippet, SnippetMetadata, SnippetVersion, SearchResult, SearchMode
from snipcontext.core.storage import StorageEngine
from snipcontext.core.search import SemanticSearch, HybridSearch
from snipcontext.config.settings import Config
