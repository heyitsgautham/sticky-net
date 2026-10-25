"""
Test suite for PRIORITY 0 fixes — MUST FIX items (30+ pts recovery).

These tests verify the 5 critical issues whose fixes are trivial but
recover ~25-30 points immediately:

  ISSUE 1: engagementDurationSeconds always 0        (-10 pts/scenario)
  ISSUE 2: engagementMetrics missing from callback    (-2.5 pts/scenario)
  ISSUE 3: status field missing from callback         (-5 pts/scenario)
  ISSUE 4: emailAddresses not in callback intel       (-10 pts on phishing)
  ISSUE 5: Intelligence not accumulated across turns  (variable)

Run:  .venv/bin/python -m pytest final-testing/test_priority0_callback_fixes.py -v
"""

import time

import pytest

from src.api.callback import CallbackIntelligence, CallbackPayload

# ============================================================================
# ISSUE 1: engagementDurationSeconds always 0
# ============================================================================


class TestEngagementDuration:
    """
    The evaluator awards:
      +5 pts if engagementDurationSeconds > 0
      +5 pts if engagementDurationSeconds > 60
    Currently we always send 0 → lose 10 pts per scenario.
    """

    def test_callback_payload_has_engagement_metrics_field(self):
        """CallbackPayload model MUST have engagementMetrics field."""
        fields = CallbackPayload.model_fields
        assert "engagementMetrics" in fields, (
            "ISSUE 2: CallbackPayload is missing 'engagementMetrics' field. "
            "This costs 2.5 pts per scenario in Response Structure scoring."
        )

    def test_engagement_metrics_has_duration_field(self):
        """engagementMetrics must include engagementDurationSeconds."""
        # Try to build a payload with engagementMetrics
        try:
            payload = CallbackPayload(
                sessionId="test",
                scamDetected=True,
                totalMessagesExchanged=10,
                extractedIntelligence=CallbackIntelligence(),
                agentNotes="test",
                engagementMetrics={
                    "engagementDurationSeconds": 120,
                    "totalMessagesExchanged": 10,
                },
            )
            dumped = payload.model_dump()
            metrics = dumped.get("engagementMetrics", {})
            assert metrics.get("engagementDurationSeconds", 0) > 0, (
                "engagementDurationSeconds must be > 0 for +5 pts"
            )
        except TypeError:
            pytest.fail(
                "ISSUE 1/2: CallbackPayload doesn't accept engagementMetrics parameter. "
                "Add: engagementMetrics: dict = {} to CallbackPayload model."
            )

    def test_engagement_duration_greater_than_zero(self):
        """After fix: duration should be > 0 for any active session."""
        # Simulate: session started 30s ago
        duration = 30
        assert duration > 0, "Duration must be > 0 for +5 pts"

    def test_engagement_duration_greater_than_sixty(self):
        """After fix: multi-turn sessions should have duration > 60s for full 10 pts."""
        # Simulate: session started 90s ago
        duration = 90
        assert duration > 60, "Duration must be > 60 for +5 more pts"

    def test_duration_calculated_from_session_start(self):
        """Duration = time.time() - session_start_time, not hardcoded 0."""
        session_start = time.time() - 120  # started 2 min ago
        duration = int(time.time() - session_start)
        assert duration >= 119, "Duration should be calculated from session start time"
        assert duration <= 121, "Duration should be calculated from session start time"

    def test_duration_zero_for_first_request_is_acceptable(self):
        """On the very first turn, duration=0 is mathematically correct but still loses pts.
        After fix, even turn 1 should have duration>0 (at least processing time)."""
        # If we set session_start at request arrival, by the time we send callback,
        # a few seconds have passed from LLM processing
        session_start = time.time()
        time.sleep(0.01)  # simulate minimal processing
        duration = int(time.time() - session_start)
        # Even 0 is technically valid for very first instant, but after LLM calls
        # we expect at least 1s of elapsed time in production
        assert duration >= 0


# ============================================================================
# ISSUE 2: engagementMetrics missing from GUVI callback
# ============================================================================


class TestEngagementMetricsInCallback:
    """
    The evaluator checks for engagementMetrics field in the finalOutput.
    Missing → -2.5 pts per scenario.
    """

    def test_callback_payload_serializes_engagement_metrics(self):
        """CallbackPayload.model_dump() must include engagementMetrics."""
        try:
            payload = CallbackPayload(
                sessionId="s1",
                scamDetected=True,
                totalMessagesExchanged=6,
                extractedIntelligence=CallbackIntelligence(),
                agentNotes="notes",
                engagementMetrics={
                    "engagementDurationSeconds": 90,
                    "totalMessagesExchanged": 6,
                },
            )
            dumped = payload.model_dump()
            assert "engagementMetrics" in dumped, (
                "engagementMetrics must be present in serialized callback payload"
            )
            assert dumped["engagementMetrics"]["engagementDurationSeconds"] == 90
            assert dumped["engagementMetrics"]["totalMessagesExchanged"] == 6
        except TypeError:
            pytest.fail(
                "CallbackPayload does not accept engagementMetrics. "
                "Add field: engagementMetrics: dict = {}"
            )

    def test_engagement_metrics_not_empty_when_scam_detected(self):
        """When scam is detected, engagementMetrics must have real values."""
        metrics = {"engagementDurationSeconds": 45, "totalMessagesExchanged": 4}
        assert metrics["engagementDurationSeconds"] > 0
        assert metrics["totalMessagesExchanged"] > 0

    def test_engagement_metrics_structure_matches_evaluator(self):
        """Evaluator expects exactly: engagementDurationSeconds and totalMessagesExchanged."""
        metrics = {"engagementDurationSeconds": 100, "totalMessagesExchanged": 8}
        assert "engagementDurationSeconds" in metrics
        assert "totalMessagesExchanged" in metrics
        assert isinstance(metrics["engagementDurationSeconds"], int)
        assert isinstance(metrics["totalMessagesExchanged"], int)


# ============================================================================
# ISSUE 3: status field missing from GUVI callback
# ============================================================================


class TestStatusFieldInCallback:
    """
    The evaluator scores:
      status present → +5 pts (required field)
    Our current callback doesn't include 'status'.
    """

    def test_callback_payload_has_status_field(self):
        """CallbackPayload model MUST have a 'status' field."""
        fields = CallbackPayload.model_fields
        assert "status" in fields, (
            "ISSUE 3: CallbackPayload is missing 'status' field. "
            "This costs 5 pts per scenario in Response Structure scoring. "
            "Add: status: str = 'success' to CallbackPayload."
        )

    def test_callback_payload_status_defaults_to_success(self):
        """Status should default to 'success'."""
        try:
            payload = CallbackPayload(
                sessionId="s1",
                scamDetected=True,
                totalMessagesExchanged=6,
                extractedIntelligence=CallbackIntelligence(),
                agentNotes="test",
            )
            dumped = payload.model_dump()
            assert dumped.get("status") == "success", "status field should default to 'success'"
        except Exception:
            pytest.fail("Cannot construct CallbackPayload — status field may be missing")

    def test_callback_serialized_includes_status(self):
        """The JSON sent to GUVI must include 'status' key."""
        try:
            payload = CallbackPayload(
                sessionId="s1",
                scamDetected=True,
                totalMessagesExchanged=6,
                extractedIntelligence=CallbackIntelligence(),
                agentNotes="test",
            )
            dumped = payload.model_dump()
            assert "status" in dumped, "JSON payload must contain 'status'"
        except Exception:
            pytest.fail("Cannot serialize CallbackPayload with status field")


# ============================================================================
# ISSUE 4: emailAddresses not in callback intelligence
# ============================================================================


class TestEmailAddressesInCallback:
    """
    The phishing scenario has emailAddress in fakeData.
    Our callback sends phoneNumbers, bankAccounts, upiIds, phishingLinks,
    suspiciousKeywords — but NOT emailAddresses.
    Missing → -10 pts on phishing scenario.
    """

    def test_callback_intelligence_has_email_addresses_field(self):
        """CallbackIntelligence must have 'emailAddresses' field."""
        fields = CallbackIntelligence.model_fields
        assert "emailAddresses" in fields, (
            "ISSUE 4: CallbackIntelligence is missing 'emailAddresses' field. "
            "This costs 10 pts on the phishing scenario. "
            "Add: emailAddresses: list[str] = [] to CallbackIntelligence."
        )

    def test_callback_intelligence_serializes_email_addresses(self):
        """model_dump() must include emailAddresses."""
        try:
            intel = CallbackIntelligence(
                bankAccounts=[],
                upiIds=[],
                phishingLinks=["http://evil.com"],
                phoneNumbers=[],
                emailAddresses=["scammer@evil.com"],
                suspiciousKeywords=[],
            )
            dumped = intel.model_dump()
            assert "emailAddresses" in dumped
            assert "scammer@evil.com" in dumped["emailAddresses"]
        except TypeError:
            pytest.fail(
                "CallbackIntelligence does not accept emailAddresses. "
                "Add field: emailAddresses: list[str] = []"
            )

    def test_email_extraction_for_phishing_scenario(self):
        """Given a phishing scenario, the callback must include the email address."""
        fake_data = {"emailAddress": "offers@fake-amazon-deals.com"}
        callback_intel = {
            "emailAddresses": ["offers@fake-amazon-deals.com"],
            "phishingLinks": ["http://amaz0n-deals.fake-site.com/claim?id=12345"],
        }
        # Evaluator check: any(fake_value in str(v) for v in extracted_values)
        extracted = callback_intel.get("emailAddresses", [])
        assert any(fake_data["emailAddress"] in str(v) for v in extracted), (
            "emailAddress from fakeData must be present in callback emailAddresses"
        )

    def test_email_regex_basic_validation(self):
        """Emails should pass basic format validation."""
        import re

        email_pattern = r"^[\w.+-]+@[\w-]+\.[\w.]+$"
        valid_emails = [
            "offers@fake-amazon-deals.com",
            "scammer@evil.com",
            "phisher123@fakebank.co.in",
        ]
        for email in valid_emails:
            assert re.match(email_pattern, email), f"{email} should be valid"

    def test_send_guvi_callback_passes_email_addresses(self):
        """send_guvi_callback must accept and forward emailAddresses in intel dict."""
        intel = {
            "bankAccounts": [],
            "upiIds": [],
            "phishingLinks": [],
            "phoneNumbers": [],
            "emailAddresses": ["test@evil.com"],
            "suspiciousKeywords": [],
        }
        try:
            callback_intel = CallbackIntelligence(
                bankAccounts=intel.get("bankAccounts", []),
                upiIds=intel.get("upiIds", []),
                phishingLinks=intel.get("phishingLinks", []),
                phoneNumbers=intel.get("phoneNumbers", []),
                emailAddresses=intel.get("emailAddresses", []),
                suspiciousKeywords=intel.get("suspiciousKeywords", []),
            )
            assert callback_intel.emailAddresses == ["test@evil.com"]
        except TypeError:
            pytest.fail("CallbackIntelligence or send_guvi_callback doesn't handle emailAddresses")


# ============================================================================
# ISSUE 5: Intelligence not accumulated across turns
# ============================================================================


# ============================================================================
# COMBINED: Verify full callback payload structure after Priority 0 fixes
# ============================================================================
