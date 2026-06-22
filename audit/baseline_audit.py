"""Baseline audit for Issue #45 — provider interface compliance and plugin system."""

from __future__ import annotations

import ast
import csv
import inspect
import json
import sys
from pathlib import Path
from typing import Any

# Ensure src is importable
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from snipcontext.providers.base import BaseProvider
from snipcontext.providers.claude import ClaudeProvider
from snipcontext.providers.cursor import CursorProvider
from snipcontext.providers.generic import GenericProvider
from snipcontext.providers.openai import OpenAIProvider

try:
    from snipcontext.providers.base import ProviderError  # type: ignore[no-redef]
except ImportError:  # Phase 0 audit runs before Phase 1 hardens it

    class ProviderError(Exception):  # type: ignore[no-redef]
        """Fallback for baseline audit before the base class defines it."""


PROVIDERS = [
    ClaudeProvider,
    CursorProvider,
    OpenAIProvider,
    GenericProvider,
]

ARTIFACT_DIR = Path(__file__).parent


def _is_stub(func: Any) -> bool:
    source = inspect.getsource(func)
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return False
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            body = node.body
            if len(body) == 1 and isinstance(body[0], ast.Pass):
                return True
            if (
                len(body) == 1
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and body[0].value.value is ...
            ):
                return True
    return False


def _signature_info(func: Any) -> dict[str, Any]:
    sig = inspect.signature(func)
    params = []
    for name, param in sig.parameters.items():
        if name == "self":
            continue
        params.append(
            {
                "name": name,
                "kind": str(param.kind),
                "default": param.default is not inspect.Parameter.empty,
                "annotation": str(param.annotation)
                if param.annotation is not inspect.Parameter.empty
                else None,
            }
        )
    return {
        "name": func.__name__,
        "parameters": params,
        "return_annotation": str(sig.return_annotation)
        if sig.return_annotation is not inspect.Signature.empty
        else None,
        "abstract": getattr(func, "__isabstractmethod__", False),
        "stub": _is_stub(func),
    }


def phase0_signature_gaps() -> dict[str, Any]:
    base_methods = {
        name: _signature_info(func)
        for name, func in inspect.getmembers(BaseProvider, predicate=inspect.isfunction)
        if not name.startswith("_")
    }

    report: dict[str, Any] = {
        "base_methods": list(base_methods.keys()),
        "providers": {},
    }

    for provider_cls in PROVIDERS:
        cls_name = provider_cls.__name__
        provider_methods = {
            name: _signature_info(func)
            for name, func in inspect.getmembers(provider_cls, predicate=inspect.isfunction)
            if not name.startswith("_") and name in base_methods
        }

        missing = [name for name in base_methods if name not in provider_methods]
        signature_diffs: dict[str, Any] = {}
        for name, base_sig in base_methods.items():
            if name not in provider_methods:
                continue
            impl_sig = provider_methods[name]
            diffs: list[str] = []
            if base_sig["abstract"] and not getattr(
                getattr(provider_cls, name), "__isabstractmethod__", False
            ):
                diffs.append("was_abstract_now_concrete")
            if impl_sig.get("stub"):
                diffs.append("stub_implementation")
            base_param_map = {p["name"]: p for p in base_sig["parameters"]}
            impl_param_map = {p["name"]: p for p in impl_sig["parameters"]}
            base_names = list(base_param_map)
            impl_names = list(impl_param_map)
            if base_names != impl_names:
                diffs.append(f"param_names differ: base={base_names} impl={impl_names}")
            for param_name in base_names:
                if param_name not in impl_param_map:
                    diffs.append(f"missing_param: {param_name}")
                    continue
                base_ann = base_param_map[param_name]["annotation"]
                impl_ann = impl_param_map[param_name]["annotation"]
                if base_ann and not impl_ann:
                    diffs.append(
                        f"param_annotation_missing: param '{param_name}' impl has no annotation"
                    )
                elif base_ann != impl_ann:
                    diffs.append(
                        f"param_annotation_mismatch: param '{param_name}' base={base_ann} impl={impl_ann}"
                    )
            if base_sig["return_annotation"] != impl_sig["return_annotation"]:
                diffs.append(
                    f"return_annotation differs: base={base_sig['return_annotation']} impl={impl_sig['return_annotation']}"
                )
            if diffs:
                signature_diffs[name] = diffs

        report["providers"][cls_name] = {
            "missing": missing,
            "signature_diffs": signature_diffs,
            "methods": list(provider_methods.keys()),
        }

    return report


def _resolve_base_return_type(base_method: Any) -> Any | None:
    annotation = inspect.signature(base_method).return_annotation
    if annotation is inspect.Signature.empty:
        return None
    if isinstance(annotation, str):
        module = inspect.getmodule(base_method)
        if module:
            try:
                return eval(annotation, module.__dict__)
            except Exception:
                return None
    return annotation


def _resolve_base_method(provider_cls: type[BaseProvider], name: str) -> Any | None:
    if not hasattr(BaseProvider, name):
        return None
    return getattr(BaseProvider, name, None)


def phase0_behavior_gaps() -> dict[str, Any]:
    class _DummyConfig:
        api_key = "test"
        model = "test-model"

    from snipcontext.core.models import Language, Snippet, SnippetMetadata

    dummy_snippet = Snippet(
        content="print('hello')",
        metadata=SnippetMetadata(
            title="Hello",
            description="test",
            language=Language.PYTHON,
            source_url="https://example.com",
            framework="fastapi",
            version="0.100",
            author="Dev",
            confidence="production",
            llm_optimized=True,
        ),
        tags=["python"],
    )

    report: dict[str, Any] = {"providers": {}}

    # Patch outgoing HTTP calls so providers with network clients don't hit the wire.
    from unittest import mock as _mock  # noqa: E402

    http_patches = [
        _mock.patch("requests.post", return_value=_mock.Mock(status_code=200, json=lambda: {})),
        _mock.patch("httpx.Client.request", return_value=_mock.Mock(status_code=200, text="")),
        _mock.patch("openai.OpenAI", return_value=_mock.Mock()),
    ]

    def _start_patches() -> list[Any]:
        started = []
        for p in http_patches:
            try:
                started.append(p.start())
            except Exception:
                pass
        return started

    def _stop_patches(items: list[Any]) -> None:
        for p in http_patches:
            try:
                p.stop()
            except Exception:
                pass

    started = _start_patches()

    for provider_cls in PROVIDERS:
        cls_name = provider_cls.__name__
        provider_report: dict[str, Any] = {
            "instantiable": False,
            "methods": {},
        }
        try:
            provider = provider_cls(include_metadata=True)
            provider_report["instantiable"] = True
        except Exception as exc:  # pragma: no cover
            provider_report["instantiation_error"] = str(exc)
            report["providers"][cls_name] = provider_report
            continue

        for method_name in ["export_single", "export_batch", "health_check"]:
            method_report: dict[str, Any] = {"called": False}
            base_method = _resolve_base_method(provider_cls, method_name)
            if not hasattr(provider, method_name):
                method_report["missing"] = True
                provider_report["methods"][method_name] = method_report
                continue
            try:
                if method_name == "export_single":
                    result = provider.export_single(dummy_snippet)  # type: ignore[arg-type]
                    method_report["has_content"] = bool(result)
                    method_report["return_type"] = type(result).__name__
                    expected_type = _resolve_base_return_type(base_method) if base_method else None
                    if expected_type is not None:
                        method_report["expected_return_type"] = str(expected_type)
                        method_report["return_type_match"] = isinstance(result, expected_type)
                elif method_name == "export_batch":
                    result = provider.export_batch([dummy_snippet], title="Batch")  # type: ignore[arg-type]
                    method_report["has_content"] = bool(result)
                    method_report["return_type"] = type(result).__name__
                    expected_type = _resolve_base_return_type(base_method) if base_method else None
                    if expected_type is not None:
                        method_report["expected_return_type"] = str(expected_type)
                        method_report["return_type_match"] = isinstance(result, expected_type)
                else:
                    result = provider.health_check()  # type: ignore[attr-defined]
                    method_report["health_result"] = result
                method_report["called"] = True
            except NotImplementedError:
                method_report["not_implemented"] = True
            except ProviderError as exc:
                method_report["provider_error"] = str(exc)
            except Exception as exc:  # pragma: no cover
                method_report["unexpected_error"] = str(exc)
            provider_report["methods"][method_name] = method_report
        report["providers"][cls_name] = provider_report

    _stop_patches(started)
    return report


def phase0_coverage_matrix() -> str:
    test_files = sorted((Path(__file__).parent.parent / "tests").rglob("*.py"))

    # Base public methods to track across providers.
    base_method_names = [
        name
        for name, _ in inspect.getmembers(BaseProvider, predicate=inspect.isfunction)
        if not name.startswith("_")
    ]

    # Provider -> method -> covered boolean.
    provider_method_map: dict[str, dict[str, bool]] = {}
    for provider_cls in PROVIDERS:
        cls_name = provider_cls.__name__
        provider_method_map[cls_name] = {name: False for name in base_method_names}

    for test_file in test_files:
        content = test_file.read_text(encoding="utf-8")

        # Lightweight call-site detection: look for <provider>.method_name( patterns.
        for provider_cls in PROVIDERS:
            cls_name = provider_cls.__name__
            for method_name in base_method_names:
                pattern = f"{cls_name}().{method_name}"
                if pattern in content:
                    provider_method_map[cls_name][method_name] = True
                pattern2 = f"provider.{method_name}"
                if pattern2 in content:
                    provider_method_map[cls_name][method_name] = True

    out = ARTIFACT_DIR / "coverage-matrix.csv"
    with out.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["provider", "method", "covered"])
        for provider_cls in PROVIDERS:
            cls_name = provider_cls.__name__
            for method_name, covered in provider_method_map[cls_name].items():
                writer.writerow([cls_name, method_name, "true" if covered else "false"])
    return str(out)


def write_summary(sig_gaps: dict[str, Any], beh_gaps: dict[str, Any], coverage_path: str) -> str:
    fixes: list[dict[str, Any]] = []
    notes: list[str] = []

    # Behavior: missing methods (only base methods, not optional extras).
    for provider, data in beh_gaps["providers"].items():
        for method, info in data.get("methods", {}).items():
            if info.get("missing"):
                fixes.append(
                    {
                        "severity": "critical",
                        "provider": provider,
                        "method": method,
                        "issue": "method missing from provider",
                    }
                )

    # Behavior: return type mismatches
    for provider, data in beh_gaps["providers"].items():
        for method, info in data.get("methods", {}).items():
            if info.get("return_type_match") is False:
                fixes.append(
                    {
                        "severity": "high",
                        "provider": provider,
                        "method": method,
                        "issue": f"return type mismatch: expected={info.get('expected_return_type')} actual={info.get('return_type')}",
                    }
                )

    # Signature: annotation mismatches
    for provider, data in sig_gaps["providers"].items():
        for method, diffs in data.get("signature_diffs", {}).items():
            for diff in diffs:
                if "param_annotation" in diff or "return_annotation differs" in diff:
                    fixes.append(
                        {
                            "severity": "medium",
                            "provider": provider,
                            "method": method,
                            "issue": diff,
                        }
                    )

    # Behavior: unexpected errors
    for provider, data in beh_gaps["providers"].items():
        for method, info in data.get("methods", {}).items():
            if info.get("unexpected_error"):
                fixes.append(
                    {
                        "severity": "high",
                        "provider": provider,
                        "method": method,
                        "issue": info["unexpected_error"],
                    }
                )

    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    fixes.sort(key=lambda item: severity_order.get(item["severity"], 99))

    lines = ["# Issue #45 Phase 0 — Baseline Audit Summary", ""]
    lines.append("## Signature Gaps")
    lines.append("")
    for provider, data in sig_gaps["providers"].items():
        lines.append(f"### {provider}")
        lines.append("")
        lines.append(f"- Missing methods: {', '.join(data['missing']) or 'None'}")
        if data["signature_diffs"]:
            lines.append("- Signature diffs:")
            for method, diffs in data["signature_diffs"].items():
                lines.append(f"  - `{method}`: {', '.join(diffs)}")
        else:
            lines.append("- Signature diffs: None")
        lines.append("")

    lines.append("## Behavior Gaps")
    lines.append("")
    lines.append(
        "> Network calls are patched for `requests`, `httpx`, and `openai` in this audit. "
        "Providers using unpatched libraries (e.g. `aiohttp`, `urllib3`, custom clients) may still touch the wire."
    )
    notes.append(
        "mock_scope: requests, httpx, openai patched; other HTTP libs are not covered by this audit."
    )
    lines.append("")
    for provider, data in beh_gaps["providers"].items():
        lines.append(f"### {provider}")
        lines.append("")
        lines.append(f"- Instantiable: {data['instantiable']}")
        if data.get("instantiation_error"):
            lines.append(f"- Instantiation error: {data['instantiation_error']}")
        for method, info in data.get("methods", {}).items():
            statuses = []
            for key in [
                "called",
                "not_implemented",
                "provider_error",
                "unexpected_error",
                "missing",
            ]:
                if info.get(key):
                    statuses.append(key)
            lines.append(f"- `{method}`: {', '.join(statuses) or 'no issues'}")
            if info.get("return_type"):
                lines.append(f"  - return type: {info['return_type']}")
            if info.get("expected_return_type"):
                lines.append(f"  - expected return type: {info['expected_return_type']}")
            if info.get("return_type_match") is False:
                lines.append("  - ⚠️ return_type_mismatch: actual does not match expected")
            if info.get("unexpected_error"):
                lines.append(f"  - error: {info['unexpected_error']}")
        lines.append("")

    lines.append("## Coverage Matrix")
    lines.append("")
    lines.append(f"- CSV: {coverage_path}")
    lines.append("")

    lines.append("## Notes")
    lines.append("")
    for note in notes:
        lines.append(f"- {note}")
    lines.append("")

    lines.append("## Prioritised Fixes")
    lines.append("")
    for item in fixes:
        lines.append(
            f"- **[{item['severity'].upper()}]** `{item['provider']}.{item['method']}` — {item['issue']}"
        )
    lines.append("")

    out = ARTIFACT_DIR / "baseline-audit-summary.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    return str(out)


def main() -> int:
    sig = phase0_signature_gaps()
    beh = phase0_behavior_gaps()
    coverage_path = phase0_coverage_matrix()

    sig_path = ARTIFACT_DIR / "signature-gaps.json"
    beh_path = ARTIFACT_DIR / "behavior-gaps.json"
    sig_path.write_text(json.dumps(sig, indent=2), encoding="utf-8")
    beh_path.write_text(json.dumps(beh, indent=2), encoding="utf-8")

    summary_path = write_summary(sig, beh, coverage_path)
    print(f"signature-gaps.json: {sig_path}")
    print(f"behavior-gaps.json: {beh_path}")
    print(f"coverage-matrix.csv: {coverage_path}")
    print(f"baseline-audit-summary.md: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
