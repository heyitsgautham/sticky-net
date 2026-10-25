"""SecurityHeadersMiddleware sets hardening headers without touching bodies or status codes."""

from collections.abc import Callable
from typing import Any
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from config.settings import Settings
from src.main import app

BASE = {
    "x-content-type-options": "nosniff",
    "x-frame-options": "DENY",
    "referrer-policy": "no-referrer",
}
API = {
    "cache-control": "no-store",
    "content-security-policy": "default-src 'none'; frame-ancestors 'none'",
}


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _assert_headers(response: Any, expected: dict[str, str]) -> None:
    for name, value in expected.items():
        assert response.headers.get(name) == value, name


def test_health_gets_api_headers_and_same_body(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
    _assert_headers(response, {**BASE, **API})


def test_analyze_fallback_reply_gets_api_headers(client: TestClient) -> None:
    response = client.post("/api/v1/analyze", json={"message": {}})
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    _assert_headers(response, {**BASE, **API})


def test_tester_page_keeps_inline_scripts_working(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    _assert_headers(response, BASE)
    # A default-src 'none' CSP would block the page's inline onclick handlers.
    assert "content-security-policy" not in response.headers


def test_auth_rejections_get_the_headers_too(
    client: TestClient, use_settings: Callable[..., Settings]
) -> None:
    response = client.post("/api/v1/analyze", json={})
    assert response.status_code == 401
    _assert_headers(response, {**BASE, **API})


def test_a_header_the_route_set_is_kept() -> None:
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse

    from src.api.middleware import SecurityHeadersMiddleware

    mini = FastAPI()
    mini.add_middleware(SecurityHeadersMiddleware)

    @mini.get("/api/cached")
    def cached() -> JSONResponse:
        return JSONResponse({"ok": True}, headers={"Cache-Control": "max-age=60"})

    response = TestClient(mini).get("/api/cached")
    assert response.headers["cache-control"] == "max-age=60"
    assert response.headers["x-frame-options"] == "DENY"


def test_cors_preflight_still_succeeds(client: TestClient) -> None:
    with patch("src.api.routes.get_detector"):
        response = client.options(
            "/api/v1/analyze",
            headers={
                "Origin": "https://hackathon.guvi.in",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "x-api-key,content-type",
            },
        )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] in ("*", "https://hackathon.guvi.in")
