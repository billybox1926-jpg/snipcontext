"""Tests for providers/ollama.py."""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

from snipcontext.core.models import Language, Snippet, SnippetMetadata
from snipcontext.providers.ollama import OllamaProvider


@pytest.fixture
def mock_config():
    """Mock config for provider tests."""
    config = MagicMock()
    config.ollama.endpoint = "http://localhost:11434"
    config.ollama.model_name = "llama3.2"
    config.ollama.timeout_seconds = 10.0
    return config


@pytest.fixture
def provider(mock_config):
    with patch("snipcontext.config.settings.get_config", return_value=mock_config):
        prov = OllamaProvider()
        prov.endpoint = "http://localhost:11434"
        prov.model_name = "llama3.2"
        prov.timeout_seconds = 10.0
        return prov


@pytest.fixture
def sample_snippet():
    now = datetime.now(timezone.utc)
    return Snippet(
        id="test-123",
        title="Test Snippet",
        content="print('hello world')",
        metadata=SnippetMetadata(
            title="Test Snippet",
            description="A test snippet",
            language=Language.PYTHON,
            framework="fastapi",
            version="1.0",
            source_url="https://example.com",
            confidence="production",
        ),
        tags=["python", "test"],
        created_at=now,
    )


def test_provider_initialization(mock_config):
    """OllamaProvider initializes with correct defaults."""
    with patch("snipcontext.config.settings.get_config", return_value=mock_config):
        prov = OllamaProvider()
        assert prov.endpoint == "http://localhost:11434"
        assert prov.model_name == "llama3.2"
        assert prov.timeout_seconds == 10.0


def test_export_single(provider, sample_snippet):
    """export_single() formats a single snippet."""
    result = provider.export_single(sample_snippet)
    assert "Test Snippet" in result
    assert "python" in result.lower()
    assert "print('hello world')" in result


def test_export_batch(provider, sample_snippet):
    """export_batch() formats multiple snippets."""
    result = provider.export_batch([sample_snippet])
    assert "Test Snippet" in result
    assert "ollama" in result.lower()


def test_set_model(provider):
    """set_model() updates model name."""
    provider.set_model("llama3.1")
    assert provider.model_name == "llama3.1"
    # Should reset discovery cache
    assert provider._models_discovered is False


def test_health_check_unavailable(provider):
    """health_check() handles connection errors gracefully."""
    # When _discover_models raises ProviderError, available_models returns []
    # and health_check returns "ok (no models discovered)"
    from snipcontext.providers.base import ProviderError
    with patch.object(provider, "_discover_models", side_effect=ProviderError("Connection refused")):
        result = provider.health_check()
        # The provider handles errors gracefully
        assert "ok" in result.lower() or "unavailable" in result.lower()


def test_discover_models_success(provider):
    """_discover_models() parses response correctly."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "models": [
            {"name": "llama3.2"},
            {"name": "codellama"},
        ]
    }
    
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.get.return_value = mock_response
    
    with patch.object(provider, "_get_client", return_value=mock_client):
        models = provider._discover_models()
    
    assert "llama3.2" in models
    assert "codellama" in models


def test_discover_models_non_200(provider):
    """_discover_models() raises ProviderError on non-200 status."""
    mock_response = MagicMock()
    mock_response.status_code = 500
    
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.get.return_value = mock_response
    
    from snipcontext.providers.base import ProviderError
    with patch.object(provider, "_get_client", return_value=mock_client):
        with pytest.raises(ProviderError):
            provider._discover_models()


def test_discover_models_invalid_json(provider):
    """_discover_models() raises ProviderError on invalid JSON."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.side_effect = ValueError("Invalid JSON")
    
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.get.return_value = mock_response
    
    from snipcontext.providers.base import ProviderError
    with patch.object(provider, "_get_client", return_value=mock_client):
        with pytest.raises(ProviderError):
            provider._discover_models()


def test_discover_models_unexpected_format(provider):
    """_discover_models() raises ProviderError on unexpected response format."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = "unexpected string format"
    
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.get.return_value = mock_response
    
    from snipcontext.providers.base import ProviderError
    with patch.object(provider, "_get_client", return_value=mock_client):
        with pytest.raises(ProviderError):
            provider._discover_models()


def test_available_models_property(provider):
    """available_models property caches results."""
    provider._models_discovered = True
    provider._available_models = ["llama3.2"]
    assert provider.available_models == ["llama3.2"]


def test_export_single_minimal_metadata(provider):
    """export_single() handles minimal metadata."""
    now = datetime.now(timezone.utc)
    minimal_snippet = Snippet(
        id="minimal",
        title="Minimal",
        content="x = 1",
        metadata=SnippetMetadata(
            title="Minimal",
            language=Language.PYTHON,
        ),
        created_at=now,
    )
    result = provider.export_single(minimal_snippet)
    assert "Minimal" in result
    assert "x = 1" in result
