"""
Test suite for SESSION STATE MANAGEMENT.

Tests the in-memory session stores needed for:
  - Session start time tracking (for engagementDurationSeconds)
  - Classification caching (skip LLM on Turn 2+)
  - Intelligence accumulation (merge intel across turns)

These are cross-cutting concerns spanning Priority 0 and Priority 1.

Run:  .venv/bin/python -m pytest final-testing/test_session_state.py -v
"""

import time
import uuid
from datetime import datetime

import pytest


# ============================================================================
# SESSION START TIME TRACKING
# ============================================================================


class TestSessionTimingTracker:
    """
    After fix: routes.py should have SESSION_START_TIMES dict.
    On first request per session, store time.time().
    On each callback, compute duration = time.time() - start.
    """

    def test_session_start_recorded_on_first_turn(self):
        """First request for a session should record start time."""
        # Simulate the tracker
        session_start_times: dict[str, float] = {}
        session_id = "session-abc"

        # Turn 1: record start
        if session_id not in session_start_times:
            session_start_times[session_id] = time.time()

        assert session_id in session_start_times
        assert session_start_times[session_id] > 0

    def test_session_start_not_overwritten_on_subsequent_turns(self):
        """Turn 2+ should NOT update the start time."""
        session_start_times: dict[str, float] = {}
        session_id = "session-abc"

        # Turn 1
        session_start_times[session_id] = 1000.0

        # Turn 2: should NOT overwrite
        if session_id not in session_start_times:
            session_start_times[session_id] = 2000.0

        assert session_start_times[session_id] == 1000.0

    def test_duration_increases_over_turns(self):
        """Duration should increase as more turns are processed."""
        start = time.time()
        time.sleep(0.05)  # simulate processing
        duration1 = time.time() - start

        time.sleep(0.05)  # more processing
        duration2 = time.time() - start

        assert duration2 > duration1, "Duration should increase over time"

    def test_duration_exceeds_60_after_realistic_conversation(self):
        """
        A 10-turn conversation with ~3s per turn = ~30s.
        With real LLM calls (8-15s), easily exceeds 60s.
        """
        # Simulate start time from 90 seconds ago
        start = time.time() - 90
        duration = int(time.time() - start)
        assert duration > 60, f"Duration {duration}s should exceed 60s for +5 pts"

    def test_multiple_sessions_tracked_independently(self):
        """Different sessions should have independent timing."""
        session_start_times: dict[str, float] = {}

        session_start_times["s1"] = time.time() - 120  # 2 minutes ago
        session_start_times["s2"] = time.time() - 30  # 30 seconds ago

        d1 = int(time.time() - session_start_times["s1"])
        d2 = int(time.time() - session_start_times["s2"])

        assert d1 > 100
        assert d2 < 50
        assert d1 != d2


# ============================================================================
# CLASSIFICATION CACHE
# ============================================================================


class TestClassificationCache:
    """
    After fix: routes.py should have SESSION_CLASSIFICATIONS dict.
    Turn 1 runs LLM classification; Turn 2+ uses cached result.
    """

    def test_cache_empty_for_new_session(self):
        cache: dict[str, dict] = {}
        assert "new-session" not in cache

    def test_cache_populated_after_turn_1(self):
        cache: dict[str, dict] = {}
        session_id = "s1"

        # Turn 1 classification
        result = {"is_scam": True, "confidence": 0.88, "scam_type": "banking_fraud"}
        cache[session_id] = result

        assert session_id in cache
        assert cache[session_id]["is_scam"] is True

    def test_cached_result_used_on_turn_2(self):
        cache = {
            "s1": {"is_scam": True, "confidence": 0.92, "scam_type": "banking_fraud"}
        }

        # Simulate Turn 2: check cache first
        session_id = "s1"
        llm_called = False
        if session_id in cache:
            detection = cache[session_id]
        else:
            detection = {"is_scam": True}  # would call LLM
            llm_called = True

        assert not llm_called
        assert detection["confidence"] == 0.92

    def test_non_scam_classification_still_cached(self):
        """Even if Turn 1 says not scam, cache it for consistency."""
        cache: dict[str, dict] = {}
        session_id = "s1"

        # Turn 1: classified as not scam
        cache[session_id] = {"is_scam": False, "confidence": 0.3}

        # Turn 2: should use cache and not re-classify
        assert cache[session_id]["is_scam"] is False

    def test_cache_handles_concurrent_sessions(self):
        """Multiple concurrent sessions should not interfere."""
        cache: dict[str, dict] = {}

        cache["s1"] = {"is_scam": True, "confidence": 0.9, "scam_type": "banking_fraud"}
        cache["s2"] = {"is_scam": True, "confidence": 0.7, "scam_type": "phishing"}
        cache["s3"] = {"is_scam": False, "confidence": 0.2}

        assert cache["s1"]["confidence"] == 0.9
        assert cache["s2"]["scam_type"] == "phishing"
        assert cache["s3"]["is_scam"] is False

    def test_cache_saves_latency(self):
        """
        Verify that cache lookup is orders of magnitude faster than LLM call.
        """
        cache = {"s1": {"is_scam": True}}

        start = time.time()
        _ = cache.get("s1")
        cache_time = time.time() - start

        # Cache lookup should be < 1ms
        assert cache_time < 0.001, f"Cache lookup took {cache_time:.6f}s, should be <1ms"


# ============================================================================
# INTELLIGENCE ACCUMULATION STORE
# ============================================================================


class TestIntelligenceAccumulationStore:
    """
    After fix: routes.py should have SESSION_INTEL dict[str, dict[str, set]].
    Each turn's extracted intel is merged (union) with accumulated intel.
    """

    def _new_store(self) -> dict[str, set]:
        return {
            "bankAccounts": set(),
            "upiIds": set(),
            "phoneNumbers": set(),
            "phishingLinks": set(),
            "emailAddresses": set(),
            "suspiciousKeywords": set(),
        }

    def test_accumulate_first_turn_intel(self):
        store = self._new_store()
        turn1 = {"phoneNumbers": ["+91-9876543210"]}

        for key, values in turn1.items():
            if key in store:
                store[key].update(values)

        assert "+91-9876543210" in store["phoneNumbers"]
        assert len(store["bankAccounts"]) == 0  # not yet extracted

    def test_accumulate_across_multiple_turns(self):
        store = self._new_store()

        # Turn 1: phone
        store["phoneNumbers"].add("+91-9876543210")
        # Turn 3: bank + UPI
        store["bankAccounts"].add("1234567890123456")
        store["upiIds"].add("scammer.fraud@fakebank")
        # Turn 5: email (phishing scenario)
        store["emailAddresses"].add("scam@evil.com")

        assert len(store["phoneNumbers"]) == 1
        assert len(store["bankAccounts"]) == 1
        assert len(store["upiIds"]) == 1
        assert len(store["emailAddresses"]) == 1

    def test_accumulation_deduplicates_exact_matches(self):
        store = self._new_store()

        # Same phone in Turn 2, 4, 6
        for _ in range(3):
            store["phoneNumbers"].add("9876543210")

        assert len(store["phoneNumbers"]) == 1

    def test_accumulation_preserves_variants(self):
        """
        Different formats of same phone = different entries.
        This is intentional — evaluator checks substring match.
        """
        store = self._new_store()
        store["phoneNumbers"].add("+91-9876543210")
        store["phoneNumbers"].add("9876543210")
        store["phoneNumbers"].add("919876543210")

        # All 3 are kept — evaluator will match any that contains fakeData value
        assert len(store["phoneNumbers"]) == 3

    def test_convert_to_callback_format(self):
        """Convert set-based store to list-based callback format."""
        store = {
            "bankAccounts": {"1234567890123456", "9876543210123456"},
            "upiIds": {"scammer@bank"},
            "phoneNumbers": set(),
            "phishingLinks": set(),
            "emailAddresses": set(),
        }

        callback_intel = {k: sorted(list(v)) for k, v in store.items()}

        assert isinstance(callback_intel["bankAccounts"], list)
        assert len(callback_intel["bankAccounts"]) == 2
        assert isinstance(callback_intel["upiIds"], list)

    def test_empty_store_produces_empty_lists(self):
        store = self._new_store()
        callback_intel = {k: list(v) for k, v in store.items()}

        for key, val in callback_intel.items():
            assert val == [], f"{key} should be empty list, got {val}"

    def test_full_bank_fraud_accumulation_scenario(self):
        """
        Simulate full bank_fraud multi-turn:
        Turn 2: phone shared
        Turn 3: bank + UPI shared
        Turn 5: phone repeated (deduplicated)
        Final callback should have all 3 items.
        """
        from scoring_helpers import score_intelligence_extraction, BANK_FRAUD_SCENARIO

        store = self._new_store()

        # Turn 2
        store["phoneNumbers"].add("+91-9876543210")
        # Turn 3
        store["bankAccounts"].add("1234567890123456")
        store["upiIds"].add("scammer.fraud@fakebank")
        # Turn 5
        store["phoneNumbers"].add("+91-9876543210")  # duplicate

        callback_intel = {k: list(v) for k, v in store.items()}
        output = {"extractedIntelligence": callback_intel}

        score = score_intelligence_extraction(output, BANK_FRAUD_SCENARIO["fakeData"])
        assert score == 30, f"Full accumulation should score 30 pts, got {score}"

    def test_full_phishing_accumulation_scenario(self):
        """
        Simulate phishing multi-turn:
        Turn 1: phishing link in initial message
        Turn 3: email shared
        """
        from scoring_helpers import score_intelligence_extraction, PHISHING_SCENARIO

        store = self._new_store()

        # Turn 1
        store["phishingLinks"].add("http://amaz0n-deals.fake-site.com/claim?id=12345")
        # Turn 3
        store["emailAddresses"].add("offers@fake-amazon-deals.com")

        callback_intel = {k: list(v) for k, v in store.items()}
        output = {"extractedIntelligence": callback_intel}

        score = score_intelligence_extraction(output, PHISHING_SCENARIO["fakeData"])
        assert score == 20, f"Full phishing accumulation should score 20 pts, got {score}"

    def test_session_store_isolation(self):
        """Different sessions should have completely independent stores."""
        stores: dict[str, dict[str, set]] = {}

        stores["s1"] = self._new_store()
        stores["s2"] = self._new_store()

        stores["s1"]["phoneNumbers"].add("1111111111")
        stores["s2"]["phoneNumbers"].add("2222222222")

        assert "1111111111" not in stores["s2"]["phoneNumbers"]
        assert "2222222222" not in stores["s1"]["phoneNumbers"]


# ============================================================================
# ROUTES.PY: Session state global dicts
# ============================================================================


class TestRoutesSessionState:
    """
    Verify that routes.py has the required session state dictionaries
    after Priority 0 and Priority 1 fixes.
    """

    def test_routes_has_session_start_times(self):
        """routes.py should define SESSION_START_TIMES dict."""
        try:
            from src.api import routes
            assert hasattr(routes, "SESSION_START_TIMES"), (
                "routes.py must define SESSION_START_TIMES: dict[str, float] = {} "
                "for tracking session timing."
            )
        except ImportError:
            pytest.fail("Cannot import src.api.routes")

    def test_routes_has_session_intel(self):
        """routes.py should define SESSION_INTEL dict for accumulation."""
        try:
            from src.api import routes
            assert hasattr(routes, "SESSION_INTEL"), (
                "routes.py must define SESSION_INTEL: dict[str, dict[str, set]] = {} "
                "for accumulating intelligence across turns."
            )
        except ImportError:
            pytest.fail("Cannot import src.api.routes")

    def test_routes_has_session_classifications(self):
        """routes.py should define SESSION_CLASSIFICATIONS dict for caching."""
        try:
            from src.api import routes
            assert hasattr(routes, "SESSION_CLASSIFICATIONS"), (
                "routes.py must define SESSION_CLASSIFICATIONS: dict[str, Any] = {} "
                "for caching classification results."
            )
        except ImportError:
            pytest.fail("Cannot import src.api.routes")
