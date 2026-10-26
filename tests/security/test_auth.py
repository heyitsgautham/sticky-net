"""The x-api-key check in APIKeyMiddleware and src.api.auth."""

from collections.abc import Callable
from typing import Any
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from config.settings import Settings
from src.api.auth import key_matches
from src.main import app

# The key the GUVI hackathon evaluator used to send. The hackathon is over, so it
# must no longer open the API.
RETIRED_EVALUATOR_KEY = "test-api-key"

# /health is exempt, so a protected route is needed. A body FastAPI rejects still
# reaches the middleware first, which is all these tests look at, and past the
# middleware it gets the evaluator-safe 200 fallback reply.
PROTECTED = "/api/v1/analyze"


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _post(client: TestClient, key: str | bytes | None) -> Any:
    headers = {"x-api-key": key} if key is not None else {}
    with patch("src.api.routes.get_detector"):
        return client.post(PROTECTED, json={"message": {}}, headers=headers)


class TestProductionMode:
    def test_missing_key_is_401(
        self, client: TestClient, use_settings: Callable[..., Settings]
    ) -> None:
        response = _post(client, None)
        assert response.status_code == 401
        assert response.json() == {"status": "error", "error": "Missing API key"}

    def test_empty_key_counts_as_missing(
        self, client: TestClient, use_settings: Callable[..., Settings]
    ) -> None:
        assert _post(client, "").status_code == 401

    def test_wrong_key_is_403(
        self, client: TestClient, use_settings: Callable[..., Settings]
    ) -> None:
        response = _post(client, "prod-key-for-test")  # one character short
        assert response.status_code == 403
        assert response.json() == {"status": "error", "error": "Invalid API key"}

    def test_configured_key_passes(
        self, client: TestClient, use_settings: Callable[..., Settings]
    ) -> None:
        assert _post(client, "prod-key-for-tests").status_code == 200

    def test_retired_evaluator_key_is_rejected(
        self, client: TestClient, use_settings: Callable[..., Settings]
    ) -> None:
        assert _post(client, RETIRED_EVALUATOR_KEY).status_code == 403

    def test_non_ascii_key_is_rejected_not_crashing(
        self, client: TestClient, use_settings: Callable[..., Settings]
    ) -> None:
        # Starlette decodes raw header bytes as latin-1, so non-ASCII keys reach the check.
        assert _post(client, "prod-key-for-testsé".encode("latin-1")).status_code == 403


class TestDebugMode:
    def test_missing_key_passes(
        self, client: TestClient, use_settings: Callable[..., Settings]
    ) -> None:
        use_settings(debug=True)
        assert _post(client, None).status_code == 200

    def test_wrong_key_is_still_403(
        self, client: TestClient, use_settings: Callable[..., Settings]
    ) -> None:
        use_settings(debug=True)
        assert _post(client, "nope").status_code == 403

    def test_retired_evaluator_key_is_not_a_debug_key(
        self, client: TestClient, use_settings: Callable[..., Settings]
    ) -> None:
        use_settings(debug=True)
        assert _post(client, RETIRED_EVALUATOR_KEY).status_code == 403


class TestKeyMatching:
    def test_key_matches_compares_every_key_in_constant_time(self) -> None:
        with patch("src.api.auth.hmac.compare_digest", return_value=False) as compare:
            assert key_matches("guess", ["a", "b", "c"]) is False
        assert compare.call_count == 3

    def test_key_matches_does_not_stop_at_the_first_match(self) -> None:
        with patch("src.api.auth.hmac.compare_digest", side_effect=[True, False]) as compare:
            assert key_matches("a", ["a", "b"]) is True
        assert compare.call_count == 2

    def test_key_matches_with_no_keys_is_false(self) -> None:
        assert key_matches("anything", []) is False

    def test_prefix_of_a_key_does_not_match(self) -> None:
        assert key_matches("prod", ["prod-key-for-tests"]) is False
