"""Provider interface compliance test for Issue #45 — Phase 1."""

from __future__ import annotations

import inspect
from typing import Any

import pytest

from snipcontext.providers.base import BaseProvider
from snipcontext.providers.claude import ClaudeProvider
from snipcontext.providers.cursor import CursorProvider
from snipcontext.providers.generic import GenericProvider
from snipcontext.providers.openai import OpenAIProvider

CONCRETE_PROVIDERS = [
    ClaudeProvider,
    CursorProvider,
    OpenAIProvider,
    GenericProvider,
]


class TestProviderInterfaceContract:
    """Dynamically verify all concrete providers satisfy BaseProvider contract."""

    @pytest.mark.parametrize("provider_cls", CONCRETE_PROVIDERS)
    def test_abstract_methods_satisfied(self, provider_cls: type[BaseProvider]) -> None:
        provider_cls()

    @pytest.mark.parametrize("provider_cls", CONCRETE_PROVIDERS)
    def test_signature_matches_base(self, provider_cls: type[BaseProvider]) -> None:
        base_methods = {
            name: func
            for name, func in inspect.getmembers(BaseProvider, predicate=inspect.isfunction)
            if not name.startswith("_")
        }
        for name, base_func in base_methods.items():
            impl = getattr(provider_cls, name)
            base_sig = inspect.signature(base_func)
            impl_sig = inspect.signature(impl)
            assert list(base_sig.parameters) == list(impl_sig.parameters)
            assert base_sig.return_annotation == impl_sig.return_annotation

    @pytest.mark.parametrize("provider_cls", CONCRETE_PROVIDERS)
    def test_health_check_returns_str(self, provider_cls: type[BaseProvider]) -> None:
        provider = provider_cls()
        result = provider.health_check()
        assert isinstance(result, str)
        assert result

    @pytest.mark.parametrize("provider_cls", CONCRETE_PROVIDERS)
    def test_export_single_signature(self, provider_cls: type[BaseProvider]) -> None:
        sig = inspect.signature(provider_cls.export_single)
        params = list(sig.parameters)
        assert params == ["self", "snippet"]
        assert str(sig.return_annotation) == "str"

    @pytest.mark.parametrize("provider_cls", CONCRETE_PROVIDERS)
    def test_export_batch_signature(self, provider_cls: type[BaseProvider]) -> None:
        sig = inspect.signature(provider_cls.export_batch)
        params = list(sig.parameters)
        assert params == ["self", "snippets", "title"]
        assert str(sig.return_annotation) == "str"


class TestProviderRegistry:
    """Verify registry surfaces work after Phase 1 interface changes."""

    def test_new_provider_must_register(self) -> None:
        class UnregisteredProvider(BaseProvider):
            name = "unregistered"

            def export_single(self, snippet: Any) -> str:
                return ""

            def export_batch(self, snippets: list[Any], title: str = "Code Context") -> str:
                return f"# {title}\n"

            def health_check(self) -> str:
                return "ok"

        # This class should satisfy the contract but not be auto-discovered
        # unless added to PluginManager. The test enforces that adding a new
        # concrete provider requires explicit registration or entry point.
        from snipcontext.plugins.base import PluginManager

        pm = PluginManager()
        pm.load_builtin_providers()
        assert "unregistered" not in pm.list_providers()
