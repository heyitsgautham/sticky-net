"""RateLimitMiddleware and the sliding-window limiter behind it."""

from collections.abc import Callable, Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from config.settings import Settings
from src.api.rate_limit import RateDecision, SlidingWindowLimiter, client_key, limiter
from src.main import app
from src.metrics import REGISTRY

KEY = "prod-key-for-tests"
LIMIT = 3
LIMITED_BODY = {"status": "error", "error": "Rate limit exceeded"}


@pytest.fixture
def limited(use_settings: Callable[..., Settings]) -> Iterator[Callable[..., Settings]]:
    """Production mode with a limit of 3 requests per minute and an empty limiter."""
    limiter.clear()
    use_settings(rate_limit_enabled=True, rate_limit_requests=LIMIT, rate_limit_window_seconds=60)
    yield use_settings
    limiter.clear()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _analyze(client: TestClient, key: str | None = KEY) -> Any:
    headers = {"x-api-key": key} if key else {}
    # A body FastAPI rejects still passes every middleware and gets the 200 fallback.
    return client.post("/api/v1/analyze", json={"message": {}}, headers=headers)


class TestMiddleware:
    def test_traffic_under_the_limit_passes_and_counts_down(
        self, limited: Callable[..., Settings], client: TestClient
    ) -> None:
        responses = [_analyze(client) for _ in range(LIMIT)]

        assert [r.status_code for r in responses] == [200] * LIMIT
        assert [r.headers["x-ratelimit-remaining"] for r in responses] == ["2", "1", "0"]
        assert all(r.headers["x-ratelimit-limit"] == str(LIMIT) for r in responses)
        assert all("retry-after" not in r.headers for r in responses)

    def test_burst_past_the_limit_gets_429_with_retry_after(
        self, limited: Callable[..., Settings], client: TestClient
    ) -> None:
        for _ in range(LIMIT):
            _analyze(client)

        response = _analyze(client)

        assert response.status_code == 429
        assert response.json() == LIMITED_BODY
        assert 1 <= int(response.headers["retry-after"]) <= 60
        assert response.headers["x-ratelimit-remaining"] == "0"
        # The refusal still carries the hardening headers.
        assert response.headers["cache-control"] == "no-store"

    def test_each_valid_key_has_its_own_allowance(
        self, limited: Callable[..., Settings], client: TestClient
    ) -> None:
        for _ in range(LIMIT):
            _analyze(client, key=None)  # 401s, counted against the address
        assert _analyze(client, key=None).status_code == 429

        assert _analyze(client, key=KEY).status_code == 200

    def test_made_up_keys_share_the_address_allowance(
        self, limited: Callable[..., Settings], client: TestClient
    ) -> None:
        statuses = [_analyze(client, key=f"guess-{i}").status_code for i in range(LIMIT + 1)]
        assert statuses == [403] * LIMIT + [429]

    def test_health_and_preflight_are_never_limited(
        self, limited: Callable[..., Settings], client: TestClient
    ) -> None:
        for _ in range(LIMIT + 2):
            assert client.get("/health").status_code == 200
        preflight = client.options(
            "/api/v1/analyze",
            headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "POST"},
        )
        assert preflight.status_code == 200

    def test_disabled_limiter_lets_everything_through(
        self, limited: Callable[..., Settings], client: TestClient
    ) -> None:
        limited(rate_limit_enabled=False, rate_limit_requests=1)
        assert [_analyze(client).status_code for _ in range(5)] == [200] * 5

    def test_refusals_are_counted(
        self, limited: Callable[..., Settings], client: TestClient
    ) -> None:
        before = REGISTRY.get_sample_value("sticky_net_rate_limited_total", {"scope": "key"}) or 0
        for _ in range(LIMIT + 2):
            _analyze(client)
        after = REGISTRY.get_sample_value("sticky_net_rate_limited_total", {"scope": "key"})
        assert after == before + 2


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


class TestSlidingWindowLimiter:
    def test_window_slides_rather_than_resetting(self) -> None:
        clock = FakeClock()
        window = SlidingWindowLimiter(clock=clock)

        assert window.hit("c", 2, 10).allowed  # t=1000
        clock.now = 1006
        assert window.hit("c", 2, 10).allowed  # t=1006
        clock.now = 1008
        assert window.hit("c", 2, 10) == RateDecision(False, 2, 0, 2)  # 1000 leaves at 1010
        clock.now = 1010
        assert window.hit("c", 2, 10).allowed
        clock.now = 1011
        assert window.hit("c", 2, 10) == RateDecision(False, 2, 0, 5)  # 1006 leaves at 1016

    def test_refused_requests_do_not_extend_the_wait(self) -> None:
        clock = FakeClock()
        window = SlidingWindowLimiter(clock=clock)
        window.hit("c", 1, 10)
        for _ in range(5):
            assert not window.hit("c", 1, 10).allowed
        clock.now += 10
        assert window.hit("c", 1, 10).allowed

    def test_clients_are_independent(self) -> None:
        window = SlidingWindowLimiter(clock=FakeClock())
        assert window.hit("a", 1, 10).allowed
        assert not window.hit("a", 1, 10).allowed
        assert window.hit("b", 1, 10).allowed

    def test_tracked_clients_are_bounded(self) -> None:
        window = SlidingWindowLimiter(max_clients=2, clock=FakeClock())
        for name in ("a", "b", "c"):
            window.hit(name, 1, 10)
        # "a" was evicted, so it starts a fresh window.
        assert window.hit("a", 1, 10).allowed
        assert not window.hit("c", 1, 10).allowed


class TestClientKey:
    def test_valid_key_is_hashed(self) -> None:
        bucket = client_key("secret-key", "1.2.3.4", key_is_valid=True)
        assert bucket.startswith("key:")
        assert "secret-key" not in bucket

    def test_invalid_or_missing_key_uses_the_address(self) -> None:
        assert client_key("guess", "1.2.3.4", key_is_valid=False) == "ip:1.2.3.4"
        assert client_key(None, "1.2.3.4", key_is_valid=False) == "ip:1.2.3.4"
        assert client_key(None, None, key_is_valid=False) == "ip:unknown"
