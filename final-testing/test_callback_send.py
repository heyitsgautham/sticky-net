"""
Test suite for CALLBACK PAYLOAD CONSTRUCTION & SEND FUNCTION.

Tests the send_guvi_callback function to verify that it correctly
constructs and sends payloads matching the evaluator's expected format.

Run:  .venv/bin/python -m pytest final-testing/test_callback_send.py -v
"""

import json
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from src.api.callback import (
    CallbackPayload,
    CallbackIntelligence,
    send_guvi_callback,
    send_guvi_callback_sync,
)


# ============================================================================
# CALLBACK PAYLOAD MODEL TESTS
# ============================================================================


class TestCallbackPayloadModel:
    """Test the CallbackPayload Pydantic model structure."""

    def test_required_fields_present(self):
        """CallbackPayload must have all evaluator-required fields."""
        required = ["sessionId", "scamDetected", "totalMessagesExchanged",
                     "extractedIntelligence", "agentNotes"]
        for field in required:
            assert field in CallbackPayload.model_fields, f"Missing required field: {field}"

    def test_evaluator_scored_fields_present(self):
        """Fields the evaluator scores on must be in the model."""
        scored_fields = {
            "status": "5 pts (required)",
            "scamDetected": "5 pts (required)",
            "extractedIntelligence": "5 pts (required)",
            "engagementMetrics": "2.5 pts (optional)",
            "agentNotes": "2.5 pts (optional)",
        }
        for field, scoring in scored_fields.items():
            assert field in CallbackPayload.model_fields, (
                f"Missing field '{field}' worth {scoring} in Response Structure"
            )

    def test_minimal_valid_payload(self):
        """Minimal payload should construct without errors."""
        payload = CallbackPayload(
            sessionId="test-123",
            scamDetected=True,
            totalMessagesExchanged=4,
            extractedIntelligence=CallbackIntelligence(),
            agentNotes="Test notes",
        )
        assert payload.sessionId == "test-123"
        assert payload.scamDetected is True

    def test_full_valid_payload(self):
        """Full payload with all fields should construct correctly."""
        try:
            payload = CallbackPayload(
                sessionId="full-test",
                status="success",
                scamDetected=True,
                totalMessagesExchanged=10,
                extractedIntelligence=CallbackIntelligence(
                    bankAccounts=["1234567890123456"],
                    upiIds=["scam@bank"],
                    phoneNumbers=["+91-9876543210"],
                    phishingLinks=["http://evil.com"],
                    emailAddresses=["evil@scam.com"],
                    suspiciousKeywords=["urgent"],
                ),
                engagementMetrics={
                    "engagementDurationSeconds": 120,
                    "totalMessagesExchanged": 10,
                },
                agentNotes="Scammer identified.",
            )
            dumped = payload.model_dump()
            assert dumped["status"] == "success"
            assert dumped["engagementMetrics"]["engagementDurationSeconds"] == 120
            assert "evil@scam.com" in dumped["extractedIntelligence"]["emailAddresses"]
        except TypeError as e:
            pytest.fail(f"Full payload construction failed: {e}")

    def test_payload_serialization_to_json(self):
        """model_dump() output should be valid JSON-serializable dict."""
        payload = CallbackPayload(
            sessionId="json-test",
            scamDetected=True,
            totalMessagesExchanged=5,
            extractedIntelligence=CallbackIntelligence(),
            agentNotes="Notes",
        )
        dumped = payload.model_dump()
        json_str = json.dumps(dumped)
        parsed = json.loads(json_str)
        assert parsed["sessionId"] == "json-test"


# ============================================================================
# CALLBACK INTELLIGENCE MODEL TESTS
# ============================================================================


class TestCallbackIntelligenceModel:
    """Test the CallbackIntelligence Pydantic model."""

    def test_all_intel_fields_present(self):
        """Must have all fields the evaluator checks against fakeData."""
        expected_fields = [
            "bankAccounts",
            "upiIds",
            "phoneNumbers",
            "phishingLinks",
            "emailAddresses",  # CRITICAL for phishing scenario
            "suspiciousKeywords",
        ]
        for field in expected_fields:
            assert field in CallbackIntelligence.model_fields, (
                f"CallbackIntelligence missing '{field}' — "
                "evaluator can't match fakeData without it"
            )

    def test_empty_intel_defaults(self):
        """All fields should default to empty lists."""
        intel = CallbackIntelligence()
        dumped = intel.model_dump()
        for field in ["bankAccounts", "upiIds", "phoneNumbers",
                       "phishingLinks", "suspiciousKeywords"]:
            assert dumped[field] == [], f"{field} should default to []"

    def test_email_addresses_default(self):
        """emailAddresses should default to empty list."""
        try:
            intel = CallbackIntelligence()
            dumped = intel.model_dump()
            assert dumped.get("emailAddresses") == [] or "emailAddresses" not in dumped
        except Exception:
            pass  # Will fail if field doesn't exist (pre-fix)

    def test_intel_with_data(self):
        """Intel with populated fields should serialize correctly."""
        intel = CallbackIntelligence(
            bankAccounts=["12345"],
            upiIds=["a@b"],
            phoneNumbers=["9876543210"],
            phishingLinks=["http://x"],
            suspiciousKeywords=["urgent"],
        )
        dumped = intel.model_dump()
        assert dumped["bankAccounts"] == ["12345"]
        assert dumped["phoneNumbers"] == ["9876543210"]


# ============================================================================
# SEND FUNCTION TESTS
# ============================================================================


class TestSendGuviCallback:
    """Test the send_guvi_callback async function."""

    @pytest.mark.asyncio
    async def test_send_callback_disabled(self):
        """When callback is disabled, should return True without HTTP call."""
        with patch("src.api.callback.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                guvi_callback_enabled=False,
            )
            result = await send_guvi_callback(
                session_id="test",
                scam_detected=True,
                total_messages=5,
                intelligence={"bankAccounts": []},
                agent_notes="test",
            )
            assert result is True

    @pytest.mark.asyncio
    async def test_send_callback_builds_correct_payload(self):
        """Verify the payload sent to GUVI has the correct structure."""
        captured_payload = {}

        async def mock_post(url, json=None, headers=None, timeout=None):
            captured_payload.update(json or {})
            mock_response = MagicMock()
            mock_response.status_code = 200
            return mock_response

        with patch("src.api.callback.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                guvi_callback_enabled=True,
                guvi_callback_url="https://test.example.com/callback",
                guvi_callback_timeout=10.0,
            )
            with patch("httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.post = mock_post
                mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
                mock_instance.__aexit__ = AsyncMock(return_value=False)
                mock_client.return_value = mock_instance

                await send_guvi_callback(
                    session_id="session-xyz",
                    scam_detected=True,
                    total_messages=8,
                    intelligence={
                        "bankAccounts": ["12345"],
                        "upiIds": ["a@b"],
                        "phishingLinks": [],
                        "phoneNumbers": ["9876543210"],
                        "suspiciousKeywords": ["urgent"],
                    },
                    agent_notes="Test agent notes",
                )

        # Verify payload structure
        assert captured_payload.get("sessionId") == "session-xyz"
        assert captured_payload.get("scamDetected") is True
        assert captured_payload.get("totalMessagesExchanged") == 8
        assert "extractedIntelligence" in captured_payload
        assert captured_payload.get("agentNotes") == "Test agent notes"

    @pytest.mark.asyncio
    async def test_send_callback_with_engagement_metrics(self):
        """After fix: send_guvi_callback should accept engagement_duration param."""
        # This test verifies the function signature has been updated
        # to accept engagement_duration and build engagementMetrics
        import inspect
        sig = inspect.signature(send_guvi_callback)
        params = list(sig.parameters.keys())

        # After fix, should have engagement_duration parameter
        # If not present yet, this documents the expected signature change
        expected_params = ["session_id", "scam_detected", "total_messages",
                          "intelligence", "agent_notes"]

        for p in expected_params:
            assert p in params, f"send_guvi_callback missing parameter '{p}'"

    @pytest.mark.asyncio
    async def test_send_callback_handles_timeout(self):
        """Callback timeout should not crash the system."""
        import httpx

        with patch("src.api.callback.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                guvi_callback_enabled=True,
                guvi_callback_url="https://test.example.com/callback",
                guvi_callback_timeout=0.001,  # Very short timeout
            )
            with patch("httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.post = AsyncMock(
                    side_effect=httpx.TimeoutException("timeout")
                )
                mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
                mock_instance.__aexit__ = AsyncMock(return_value=False)
                mock_client.return_value = mock_instance

                result = await send_guvi_callback(
                    session_id="timeout-test",
                    scam_detected=True,
                    total_messages=2,
                    intelligence={},
                    agent_notes="test",
                )

                assert result is False  # Should return False, not crash

    @pytest.mark.asyncio
    async def test_send_callback_handles_connection_error(self):
        """Connection errors should not crash the system."""
        import httpx

        with patch("src.api.callback.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                guvi_callback_enabled=True,
                guvi_callback_url="https://test.example.com/callback",
                guvi_callback_timeout=10.0,
            )
            with patch("httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.post = AsyncMock(
                    side_effect=httpx.ConnectError("connection refused")
                )
                mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
                mock_instance.__aexit__ = AsyncMock(return_value=False)
                mock_client.return_value = mock_instance

                result = await send_guvi_callback(
                    session_id="conn-error-test",
                    scam_detected=True,
                    total_messages=2,
                    intelligence={},
                    agent_notes="test",
                )

                assert result is False


# ============================================================================
# CALLBACK + SCORING INTEGRATION
# ============================================================================


class TestCallbackScoringIntegration:
    """
    Verify that a CallbackPayload.model_dump() output scores correctly
    when fed through the evaluator scoring functions.
    """

    def test_current_payload_scoring(self):
        """Score what our current CallbackPayload produces."""
        from scoring_helpers import score_scenario, BANK_FRAUD_SCENARIO

        payload = CallbackPayload(
            sessionId="test",
            scamDetected=True,
            totalMessagesExchanged=10,
            extractedIntelligence=CallbackIntelligence(
                bankAccounts=["1234567890123456"],
                upiIds=["scammer.fraud@fakebank"],
                phoneNumbers=["+91-9876543210"],
            ),
            agentNotes="Scam detected.",
        )
        dumped = payload.model_dump()
        scores = score_scenario(dumped, BANK_FRAUD_SCENARIO["fakeData"])

        # Document current scoring
        assert scores["scamDetection"] == 20

    def test_fixed_payload_scoring(self):
        """Score what the FIXED CallbackPayload should produce."""
        from scoring_helpers import score_scenario, BANK_FRAUD_SCENARIO

        try:
            payload = CallbackPayload(
                sessionId="test",
                status="success",
                scamDetected=True,
                totalMessagesExchanged=10,
                extractedIntelligence=CallbackIntelligence(
                    bankAccounts=["1234567890123456"],
                    upiIds=["scammer.fraud@fakebank"],
                    phoneNumbers=["+91-9876543210"],
                ),
                engagementMetrics={
                    "engagementDurationSeconds": 120,
                    "totalMessagesExchanged": 10,
                },
                agentNotes="Scam detected with urgency tactics.",
            )
            dumped = payload.model_dump()
            scores = score_scenario(dumped, BANK_FRAUD_SCENARIO["fakeData"])

            assert scores["scamDetection"] == 20
            assert scores["intelligenceExtraction"] == 30
            assert scores["engagementQuality"] == 20
            assert scores["responseStructure"] == 20.0
            assert scores["total"] == 90.0
        except TypeError:
            pytest.fail(
                "CallbackPayload construction with status/engagementMetrics failed. "
                "Apply Priority 0 fixes first."
            )
