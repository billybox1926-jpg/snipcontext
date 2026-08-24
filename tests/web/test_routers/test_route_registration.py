"""Route registration tests (issue #200).

``snippets.router`` and ``web_ui.router`` both define ``/snippets`` and
``/snippets/{snippet_id}``. Both were included without a prefix, so FastAPI
resolved the first match and every ``web_ui`` snippet handler became
unreachable dead code — discovered while fixing #198, whose regression tests
had to call the handler directly.

``web_ui.router`` is now mounted under ``/api``, which is both the namespace
``serve_frontend()`` reserves and the base the frontend requests.
"""

from __future__ import annotations

from typing import Any

import pytest

fastapi = pytest.importorskip("fastapi")

from snipcontext.web.app import create_app  # noqa: E402


def _walk(routes: Any, prefix: str = "") -> Any:
    """Yield (methods, full_path, owner) for every endpoint in the app.

    Recent FastAPI wraps ``include_router`` results in ``_IncludedRouter``,
    whose sub-routes are reachable via ``original_router`` and whose
    include-time prefix lives on ``include_context``. Walking ``app.routes``
    naively (as the issue's repro did) misses every included route.
    """
    for route in routes:
        inner = getattr(route, "original_router", None)
        if inner is not None:
            ctx = getattr(route, "include_context", None)
            yield from _walk(inner.routes, prefix + (getattr(ctx, "prefix", "") or ""))
            continue
        endpoint = getattr(route, "endpoint", None)
        if endpoint is None:
            continue
        methods = sorted(getattr(route, "methods", None) or []) or ["WS"]
        path = prefix + (getattr(route, "path", "") or "")
        yield methods, path, f"{endpoint.__module__}.{endpoint.__name__}"


@pytest.fixture
def app() -> Any:
    return create_app()


class TestRouteUniqueness:
    """Every (method, path) pair must resolve to exactly one handler."""

    def test_no_duplicate_route_registrations(self, app: Any) -> None:
        owners: dict[tuple[str, str], list[str]] = {}
        for methods, path, owner in _walk(app.routes):
            for method in methods:
                owners.setdefault((method, path), []).append(owner)

        duplicates = {key: value for key, value in owners.items() if len(value) > 1}
        assert not duplicates, (
            "each (method, path) must have exactly one handler; "
            f"shadowed routes: { {f'{m} {p}': o for (m, p), o in duplicates.items()} }"
        )

    def test_walker_finds_included_routes(self, app: Any) -> None:
        """Guard the helper itself — a broken walker would vacuously pass above."""
        paths = {path for _, path, _ in _walk(app.routes)}
        assert "/snippets" in paths, "canonical snippets router not discovered"
        assert "/api/snippets" in paths, "prefixed web_ui router not discovered"


class TestRouterSeparation:
    """The two surfaces stay distinct and each keeps its own handler."""

    def test_canonical_snippets_routes_are_unprefixed(self, app: Any) -> None:
        owners = {
            (tuple(m), p): o
            for m, p, o in _walk(app.routes)
            if p in {"/snippets", "/snippets/{snippet_id}"}
        }
        assert owners, "canonical /snippets routes missing"
        for owner in owners.values():
            assert "routers.snippets" in owner, f"unexpected owner for canonical route: {owner}"

    def test_web_ui_routes_are_prefixed(self, app: Any) -> None:
        web_ui_paths = {p for _, p, o in _walk(app.routes) if ".routers.web_ui." in o}
        assert web_ui_paths, "no web_ui routes registered"
        unprefixed = {p for p in web_ui_paths if not p.startswith("/api/")}
        assert not unprefixed, f"web_ui routes must live under /api: {sorted(unprefixed)}"

    def test_web_ui_update_handler_is_registered(self, app: Any) -> None:
        """The handler #198 fixed must actually be routable."""
        put_owners = [
            o for m, p, o in _walk(app.routes) if p == "/api/snippets/{snippet_id}" and "PUT" in m
        ]
        assert put_owners == ["snipcontext.web.routers.web_ui.update_snippet"], put_owners


class TestWebUiReachableOverHttp:
    """The previously-dead handlers now answer real requests."""

    @pytest.fixture
    def _client(self, client: Any) -> Any:
        return client

    def _create(self, client: Any) -> str:
        resp = client.post(
            "/snippets",
            json={"title": "T", "content": "x = 1", "description": "d", "tags": []},
        )
        assert resp.status_code == 201, resp.text
        return str(resp.json()["id"])

    def test_web_ui_endpoints_respond(self, client: Any) -> None:
        for path in ("/api/snippets", "/api/tags"):
            resp = client.get(path)
            assert resp.status_code == 200, f"{path} -> {resp.status_code} {resp.text[:200]}"

    def test_web_ui_put_accepts_partial_body(self, client: Any) -> None:
        """web_ui takes a loose dict; the canonical router requires the full model."""
        snippet_id = self._create(client)

        resp = client.put(f"/api/snippets/{snippet_id}", json={"language": "rust"})
        assert resp.status_code == 200, resp.text
        assert resp.json()["language"] == "rust"

    def test_web_ui_put_rejects_invalid_language(self, client: Any) -> None:
        """The #198 fix is now enforced over HTTP, not just at unit level."""
        snippet_id = self._create(client)

        resp = client.put(f"/api/snippets/{snippet_id}", json={"language": "not-a-language"})
        assert resp.status_code == 422, resp.text
        assert "not-a-language" in resp.json()["detail"]

    def test_canonical_put_still_requires_full_model(self, client: Any) -> None:
        """The canonical surface is unchanged by the prefix move."""
        snippet_id = self._create(client)

        resp = client.put(f"/snippets/{snippet_id}", json={"language": "rust"})
        assert resp.status_code == 422, resp.text
        missing = {tuple(err["loc"]) for err in resp.json()["detail"]}
        assert ("body", "content") in missing

    def test_websocket_is_reachable_at_prefixed_path(self, client: Any) -> None:
        with client.websocket_connect("/api/ws"):
            pass
