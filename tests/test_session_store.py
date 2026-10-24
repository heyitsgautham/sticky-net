"""Tests for the in-memory session store and its Firestore write-through."""

import uuid
from collections.abc import Iterator
from typing import Any

import pytest

from src.api import session_store
from src.api.schemas import ExtractedIntelligence
from src.detection.detector import DetectionResult


class _FakeSnapshot:
    def __init__(self, data: dict[str, Any] | None) -> None:
        self._data = data
        self.exists = data is not None

    def to_dict(self) -> dict[str, Any]:
        return dict(self._data or {})


class _FakeDocument:
    def __init__(self, store: dict[str, dict[str, Any]], doc_id: str) -> None:
        self._store, self._id = store, doc_id

    def get(self) -> _FakeSnapshot:
        return _FakeSnapshot(self._store.get(self._id))

    def set(self, data: dict[str, Any], merge: bool = False) -> None:
        current = self._store.get(self._id, {}) if merge else {}
        self._store[self._id] = {**current, **data}


class FakeFirestore:
    """Just enough of firestore.Client for session_store: collection().document()."""

    def __init__(self) -> None:
        self.docs: dict[str, dict[str, Any]] = {}

    def collection(self, name: str) -> "FakeFirestore":
        assert name == session_store.FIRESTORE_COLLECTION
        return self

    def document(self, doc_id: str) -> _FakeDocument:
        return _FakeDocument(self.docs, doc_id)


@pytest.fixture
def firestore(monkeypatch: pytest.MonkeyPatch) -> Iterator[FakeFirestore]:
    """Turn on Firestore persistence backed by an in-memory fake."""
    fake = FakeFirestore()
    monkeypatch.setattr(session_store, "_firestore_client", fake)
    monkeypatch.setattr(session_store, "_firestore_available", True)
    yield fake


def _forget_in_memory(session_id: str) -> None:
    """Simulate a fresh Cloud Run instance that has never seen this session."""
    for cache in (
        session_store._START_TIMES,
        session_store._INTEL,
        session_store._DETECTIONS,
    ):
        cache.pop(session_id, None)


@pytest.fixture
def session_id() -> str:
    return f"test-{uuid.uuid4()}"


class TestInMemory:
    def test_unknown_session_has_no_start_time(self, session_id: str) -> None:
        assert session_store.get_session_start_time(session_id) is None

    def test_start_time_is_fixed_at_first_call(self, session_id: str) -> None:
        first = session_store.init_session_start_time(session_id)
        assert session_store.init_session_start_time(session_id) == first

    def test_accumulate_dedupes_across_turns(self, session_id: str) -> None:
        session_store.accumulate_intel(
            session_id, ExtractedIntelligence(phoneNumbers=["+919876543210"])
        )
        result = session_store.accumulate_intel(
            session_id,
            ExtractedIntelligence(
                phoneNumbers=["+919876543210"],
                upiIds=["fraud@okaxis"],
                caseIds=["REF-1"],
            ),
        )
        assert result["phoneNumbers"] == ["+919876543210"]
        assert result["upiIds"] == ["fraud@okaxis"]
        assert result["caseIds"] == ["REF-1"]
        assert result["bankAccounts"] == []

    def test_accumulate_returns_every_callback_key(self, session_id: str) -> None:
        result = session_store.accumulate_intel(session_id, ExtractedIntelligence())
        assert set(result) == {
            "bankAccounts",
            "upiIds",
            "phoneNumbers",
            "phishingLinks",
            "emailAddresses",
            "suspiciousKeywords",
            "caseIds",
            "policyNumbers",
            "orderNumbers",
        }

    def test_detection_round_trips(self, session_id: str) -> None:
        detection = DetectionResult(is_scam=True, confidence=0.9, scam_type="job_offer")
        session_store.store_detection_result(session_id, detection)
        assert session_store.get_previous_detection(session_id) is detection


class TestFirestoreWriteThrough:
    def test_start_time_survives_a_new_instance(
        self, firestore: FakeFirestore, session_id: str
    ) -> None:
        start = session_store.init_session_start_time(session_id)
        _forget_in_memory(session_id)

        assert session_store.get_session_start_time(session_id) == start

    def test_intel_survives_a_new_instance(self, firestore: FakeFirestore, session_id: str) -> None:
        session_store.init_session_start_time(session_id)
        session_store.accumulate_intel(
            session_id, ExtractedIntelligence(bankAccounts=["123456789012"])
        )
        _forget_in_memory(session_id)

        intel = session_store.get_or_init_session_intel(session_id)
        assert intel["bankAccounts"] == {"123456789012"}

    def test_scam_detection_survives_a_new_instance(
        self, firestore: FakeFirestore, session_id: str
    ) -> None:
        session_store.store_detection_result(
            session_id, DetectionResult(is_scam=True, confidence=0.75, scam_type="impersonation")
        )
        _forget_in_memory(session_id)

        restored = session_store.get_previous_detection(session_id)
        assert restored is not None
        assert restored.is_scam is True
        assert restored.scam_type == "impersonation"
        assert restored.confidence == 0.75

    def test_non_scam_detection_is_not_restored(
        self, firestore: FakeFirestore, session_id: str
    ) -> None:
        session_store.store_detection_result(
            session_id, DetectionResult(is_scam=False, confidence=0.1)
        )
        _forget_in_memory(session_id)

        assert session_store.get_previous_detection(session_id) is None

    def test_firestore_errors_fall_back_to_memory(
        self, monkeypatch: pytest.MonkeyPatch, session_id: str
    ) -> None:
        class BrokenFirestore:
            def collection(self, name: str) -> "BrokenFirestore":
                raise ConnectionError("firestore down")

        monkeypatch.setattr(session_store, "_firestore_client", BrokenFirestore())
        monkeypatch.setattr(session_store, "_firestore_available", True)

        start = session_store.init_session_start_time(session_id)
        result = session_store.accumulate_intel(session_id, ExtractedIntelligence(upiIds=["x@ybl"]))

        assert session_store.get_session_start_time(session_id) == start
        assert result["upiIds"] == ["x@ybl"]


def test_client_init_failure_disables_firestore(monkeypatch: pytest.MonkeyPatch) -> None:
    """A Firestore client that cannot start is tried once, then skipped."""
    calls = []

    def broken_client(**kwargs: Any) -> None:
        calls.append(kwargs)
        raise RuntimeError("no credentials")

    monkeypatch.setattr("google.cloud.firestore.Client", broken_client)
    monkeypatch.setattr(session_store, "_firestore_available", None)
    monkeypatch.setattr(session_store, "_firestore_client", None)

    assert session_store._get_firestore_client() is None
    assert session_store._get_firestore_client() is None
    assert len(calls) == 1
