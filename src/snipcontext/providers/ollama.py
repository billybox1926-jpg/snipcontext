"""Ollama local model export provider.

The provider formats snippets for Ollama workflows and optionally discovers
available local models via the Ollama HTTP API.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from snipcontext.core.sanitization import sanitize_code, sanitize_text
from snipcontext.plugins.base import PluginManifest
from snipcontext.providers.base import BaseProvider, ExportFormat, EXPORT_VERSION, ProviderError

if TYPE_CHECKING:
    from snipcontext.core.models import Snippet


class OllamaProvider(BaseProvider):
    """Local Ollama provider with optional model discovery and health checks."""

    manifest = PluginManifest(name="ollama", version="0.1.0", requires=["snipcontext>=0.3.0"])
    name = "ollama"
    description = "Local Ollama prompt format — use with a local Ollama instance"
    format = ExportFormat.PROMPT
    DEFAULT_ENDPOINT = "http://localhost:11434"
    DEFAULT_MODEL = "llama3.2"
    DEFAULT_TIMEOUT = 10.0

    def __init__(
        self,
        include_metadata: bool = True,
        endpoint: str | None = None,
        model_name: str | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        super().__init__(include_metadata=include_metadata)
        from snipcontext.config.settings import get_config

        config = get_config()
        self.endpoint = endpoint or config.ollama.endpoint or self.DEFAULT_ENDPOINT
        self.model_name = model_name or config.ollama.model_name or self.DEFAULT_MODEL
        self.timeout_seconds = timeout_seconds or config.ollama.timeout_seconds or self.DEFAULT_TIMEOUT
        self._models_discovered = False
        self._available_models: list[str] = []

    def _get_client(self):
        try:
            import httpx
        except ImportError as exc:
            raise ProviderError(
                "Ollama support requires optional dependency 'httpx'. "
                "Install with: pip install snipcontext[ollama] or pip install snipcontext[all]"
            ) from exc
        return httpx.Client(timeout=self.timeout_seconds)

    def _model_endpoint(self) -> str:
        return f"{self.endpoint.rstrip('/')}/api/models"

    def _discover_models(self) -> list[str]:
        try:
            with self._get_client() as client:
                response = client.get(self._model_endpoint())
        except Exception as exc:
            raise ProviderError(
                f"Unable to connect to Ollama at {self.endpoint}: {exc}"
            ) from exc

        if response.status_code != 200:
            raise ProviderError(
                f"Ollama returned unexpected status {response.status_code} from {self._model_endpoint()}"
            )

        try:
            data = response.json()
        except Exception as exc:
            raise ProviderError("Ollama model response was not valid JSON") from exc

        models: list[str] = []
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and item.get("name"):
                    models.append(str(item["name"]))
        elif isinstance(data, dict) and "models" in data:
            for item in data["models"]:
                if isinstance(item, dict) and item.get("name"):
                    models.append(str(item["name"]))
        else:
            raise ProviderError("Unexpected response format from Ollama /api/models")

        self._available_models = models
        self._models_discovered = True
        return models

    @property
    def available_models(self) -> list[str]:
        if not self._models_discovered:
            try:
                self._discover_models()
            except ProviderError:
                self._available_models = []
                self._models_discovered = True
        return self._available_models

    def export_single(self, snippet: "Snippet") -> str:
        safe_title = sanitize_text(snippet.metadata.title or "Untitled")
        lines = [
            f"### Ollama snippet: {safe_title}",
            f"### Model: {self.model_name}",
            "",
        ]

        if self.include_metadata:
            if snippet.metadata.description:
                lines.append(f"Description: {sanitize_text(snippet.metadata.description)}")
            lines.append(f"Language: {snippet.metadata.language.value}")
            if snippet.metadata.framework:
                lines.append(f"Framework: {sanitize_text(snippet.metadata.framework)}")
            if snippet.metadata.version:
                lines.append(f"Version: {sanitize_text(snippet.metadata.version)}")
            if snippet.metadata.source_url:
                lines.append(f"Source: {sanitize_text(snippet.metadata.source_url)}")
            if snippet.tags:
                lines.append(f"Tags: {', '.join(sanitize_text(t) for t in snippet.tags)}")
            if snippet.metadata.confidence:
                lines.append(f"Confidence: {sanitize_text(snippet.metadata.confidence)}")
            lines.append("")

        lines.extend(
            [
                f"```{snippet.metadata.language.value}",
                sanitize_code(snippet.content),
                "```",
                "",
            ]
        )
        return "\n".join(lines)

    def export_batch(self, snippets: list["Snippet"], title: str = "Code Context") -> str:
        safe_title = sanitize_text(title)
        lines = [
            f"### Ollama export: {safe_title}",
            f"### Model: {self.model_name}",
            f"### Use with: ollama generate --model {self.model_name}",
            f"### Export schema version: {EXPORT_VERSION}",
            "",
        ]
        for snippet in snippets:
            lines.append(self.export_single(snippet))
        return "\n".join(lines)

    def health_check(self) -> str:
        try:
            models = self.available_models
        except ProviderError as exc:
            return f"unavailable: {exc}"

        if models:
            return f"ok ({len(models)} models available)"
        return "ok (no models discovered)"

    def set_model(self, model_name: str) -> None:
        self.model_name = model_name
        self._models_discovered = False
        self._available_models = []
