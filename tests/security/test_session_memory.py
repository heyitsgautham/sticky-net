"""The in-memory session caches stay bounded however many session IDs arrive.

Anyone holding the public evaluator key can send a fresh sessionId on every request.
Without a bound, each one adds entries to the caches until the Cloud Run instance
runs out of memory.
"""

import uuid
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

import src.api.session_store as session_store
from src.api.bounded_cache import BoundedCache
from src.api.schemas import ExtractedIntelligence
from src.main import app

CACHES = ("_START_TIMES", "_INTEL", "_DETECTIONS", "_CLASSIFICATIONS")


@pytest.fixture
def small_caches(monkeypatch: pytest.MonkeyPatch) -> Iterator[int]:
    limit = 5
    for name in CACHES:
        monkeypatch.setattr(session_store, name, BoundedCache[object](limit))
    yield limit


def test_flood_of_new_sessions_keeps_every_cache_bounded(small_caches: int) -> None:
    client = TestClient(app)
    for _ in range(small_caches * 3):
        body = {
            "sessionId": f"flood-{uuid.uuid4()}",
            "message": {
                "sender": "scammer",
                "text": "Your SBI account is blocked, pay to x@okaxis",
                "timestamp": "2026-01-21T10:15:30Z",
            },
        }
        assert client.post("/api/v1/analyze", json=body).status_code == 200

    for name in CACHES:
        assert len(getattr(session_store, name)) <= small_caches, name


def test_active_session_survives_while_others_arrive(small_caches: int) -> None:
    active = "active-session"
    session_store.init_session_start_time(active)
    session_store.accumulate_intel(active, ExtractedIntelligence(upiIds=["keep@okaxis"]))

    for i in range(small_caches * 2):
        session_store.init_session_start_time(f"other-{i}")
        # The evaluator's own session keeps sending turns, which keeps it recent.
        session_store.get_session_start_time(active)
        session_store.get_or_init_session_intel(active)

    assert session_store.get_session_start_time(active) is not None
    assert session_store.get_or_init_session_intel(active)["upiIds"] == {"keep@okaxis"}


def test_default_limit_comes_from_settings() -> None:
    from config.settings import get_settings

    assert session_store._START_TIMES.maxsize == get_settings().session_cache_max_entries


class TestBoundedCache:
    def test_evicts_least_recently_used(self) -> None:
        cache = BoundedCache[int](2)
        cache["a"] = 1
        cache["b"] = 2
        _ = cache["a"]  # a is now the most recent
        cache["c"] = 3
        assert list(cache) == ["a", "c"]

    def test_overwrite_refreshes_without_growing(self) -> None:
        cache = BoundedCache[int](2)
        cache["a"] = 1
        cache["b"] = 2
        cache["a"] = 10
        cache["c"] = 3
        assert dict(cache) == {"a": 10, "c": 3}

    def test_get_setdefault_pop_and_membership(self) -> None:
        cache = BoundedCache[int](3)
        assert cache.get("x") is None
        assert cache.setdefault("x", 1) == 1
        assert cache.setdefault("x", 2) == 1
        assert "x" in cache
        assert cache.pop("x") == 1
        assert cache.pop("x", None) is None
        with pytest.raises(KeyError):
            _ = cache["x"]

    def test_rejects_a_non_positive_size(self) -> None:
        with pytest.raises(ValueError, match="maxsize"):
            BoundedCache[int](0)
