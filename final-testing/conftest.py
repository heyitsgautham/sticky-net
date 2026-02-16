"""
Shared fixtures and helpers for final-testing suite.

These tests mirror the GUVI hackathon evaluator scoring logic exactly,
so we can verify each priority fix recovers the expected points.
"""

import os
import sys
import time
import uuid
from datetime import datetime, timedelta
from typing import Any

# Add this directory to sys.path so scoring_helpers can be imported
sys.path.insert(0, os.path.dirname(__file__))

# Set test environment variables BEFORE any project imports
os.environ.setdefault("API_KEY", "test-api-key")
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "test-project")
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "global")
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("GUVI_CALLBACK_ENABLED", "false")

import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.api.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    ExtractedIntelligence,
    EngagementMetrics,
    HoneyPotResponse,
    Message,
    Metadata,
    ConversationMessage,
)
from src.api.callback import CallbackPayload, CallbackIntelligence


# ============================================================================
# EVALUATOR SCORING ENGINE — mirrors GUVI hackathon evaluator exactly
# ============================================================================

# Mapping from scenario fakeData keys to callback extractedIntelligence keys
FAKE_DATA_KEY_MAPPING = {
    "bankAccount": "bankAccounts",
    "upiId": "upiIds",
    "phoneNumber": "phoneNumbers",
    "phishingLink": "phishingLinks",
    "emailAddress": "emailAddresses",
}


def score_scam_detection(final_output: dict) -> int:
    """Score scam detection (max 20 pts). scamDetected=true → 20, else → 0."""
    return 20 if final_output.get("scamDetected", False) else 0


def score_intelligence_extraction(final_output: dict, fake_data: dict) -> int:
    """
    Score intelligence extraction (max 40 pts).
    10 pts per fakeData item found in extractedIntelligence.
    """
    extracted = final_output.get("extractedIntelligence", {})
    points = 0

    for fake_key, fake_value in fake_data.items():
        output_key = FAKE_DATA_KEY_MAPPING.get(fake_key, fake_key)
        extracted_values = extracted.get(output_key, [])

        if isinstance(extracted_values, list):
            if any(fake_value in str(v) for v in extracted_values):
                points += 10
        elif isinstance(extracted_values, str):
            if fake_value in extracted_values:
                points += 10

    return min(points, 40)


def score_engagement_quality(final_output: dict) -> int:
    """
    Score engagement quality (max 20 pts).
    - duration > 0: +5
    - duration > 60: +5
    - messages > 0: +5
    - messages >= 5: +5
    """
    metrics = final_output.get("engagementMetrics", {})
    duration = metrics.get("engagementDurationSeconds", 0)
    messages = metrics.get("totalMessagesExchanged", 0)

    points = 0
    if duration > 0:
        points += 5
    if duration > 60:
        points += 5
    if messages > 0:
        points += 5
    if messages >= 5:
        points += 5
    return points


def score_response_structure(final_output: dict) -> float:
    """
    Score response structure (max 20 pts).
    Required: status (+5), scamDetected (+5), extractedIntelligence (+5)
    Optional: engagementMetrics (+2.5), agentNotes (+2.5)
    """
    points = 0.0
    required_fields = ["status", "scamDetected", "extractedIntelligence"]
    optional_fields = ["engagementMetrics", "agentNotes"]

    for field in required_fields:
        if field in final_output:
            points += 5.0

    for field in optional_fields:
        if field in final_output and final_output[field]:
            points += 2.5

    return min(points, 20.0)


def score_scenario(final_output: dict, fake_data: dict) -> dict:
    """
    Full per-scenario scoring. Returns breakdown and total (max 100).
    """
    sd = score_scam_detection(final_output)
    ie = score_intelligence_extraction(final_output, fake_data)
    eq = score_engagement_quality(final_output)
    rs = score_response_structure(final_output)
    return {
        "scamDetection": sd,
        "intelligenceExtraction": ie,
        "engagementQuality": eq,
        "responseStructure": rs,
        "total": sd + ie + eq + rs,
    }


def weighted_final_score(scenario_scores: list[dict], weights: list[float]) -> float:
    """
    Compute weighted average across scenarios.
    scenario_scores: list of score dicts from score_scenario()
    weights: list of floats that sum to 1.0
    """
    assert len(scenario_scores) == len(weights)
    return sum(s["total"] * w for s, w in zip(scenario_scores, weights))


# ============================================================================
# SAMPLE SCENARIOS — from SAMPLE_CASE.md
# ============================================================================

BANK_FRAUD_SCENARIO = {
    "scenarioId": "bank_fraud",
    "name": "Bank Fraud Detection",
    "scamType": "bank_fraud",
    "initialMessage": (
        "URGENT: Your SBI account has been compromised. Your account will be "
        "blocked in 2 hours. Share your account number and OTP immediately to "
        "verify your identity."
    ),
    "metadata": {"channel": "SMS", "language": "English", "locale": "IN"},
    "weight": 10,
    "maxTurns": 10,
    "fakeData": {
        "bankAccount": "1234567890123456",
        "upiId": "scammer.fraud@fakebank",
        "phoneNumber": "+91-9876543210",
    },
}

UPI_FRAUD_SCENARIO = {
    "scenarioId": "upi_fraud",
    "name": "UPI Fraud Multi-turn",
    "scamType": "upi_fraud",
    "initialMessage": (
        "Congratulations! You have won a cashback of Rs. 5000 from Paytm. "
        "To claim your reward, please verify your UPI details. This is from "
        "official customer support."
    ),
    "metadata": {"channel": "WhatsApp", "language": "English", "locale": "IN"},
    "weight": 10,
    "maxTurns": 10,
    "fakeData": {
        "upiId": "cashback.scam@fakeupi",
        "phoneNumber": "+91-8765432109",
    },
}

PHISHING_SCENARIO = {
    "scenarioId": "phishing_link",
    "name": "Phishing Link Detection",
    "scamType": "phishing",
    "initialMessage": (
        "You have been selected for iPhone 15 Pro at just Rs. 999! Click here "
        "to claim: http://amaz0n-deals.fake-site.com/claim?id=12345. Offer "
        "expires in 10 minutes!"
    ),
    "metadata": {"channel": "Email", "language": "English", "locale": "IN"},
    "weight": 10,
    "maxTurns": 10,
    "fakeData": {
        "phishingLink": "http://amaz0n-deals.fake-site.com/claim?id=12345",
        "emailAddress": "offers@fake-amazon-deals.com",
    },
}

ALL_SCENARIOS = [BANK_FRAUD_SCENARIO, UPI_FRAUD_SCENARIO, PHISHING_SCENARIO]

# Normalized weights for 3 scenarios (35%, 35%, 30%)
SCENARIO_WEIGHTS = [0.35, 0.35, 0.30]


# ============================================================================
# MULTI-TURN CONVERSATION BUILDERS
# ============================================================================


def build_scammer_followups(scenario: dict) -> list[str]:
    """
    Build realistic scammer follow-up messages that embed fakeData.
    These simulate what the GUVI AI scammer would say across turns.
    """
    fake = scenario["fakeData"]
    scenario_id = scenario["scenarioId"]

    if scenario_id == "bank_fraud":
        return [
            # Turn 2 — share phone
            f"Ma'am, I am calling from SBI fraud department. You can verify by calling me back at {fake['phoneNumber']}. Please hurry.",
            # Turn 3 — share bank + UPI
            f"I see your account number {fake['bankAccount']} has suspicious activity. Please send Rs 1 to {fake['upiId']} to verify your identity.",
            # Turn 4 — urgency
            "Ma'am time is running out. If you don't verify now your account will be permanently blocked. Please share your OTP.",
            # Turn 5 — re-share details
            f"For your convenience, you can also use UPI ID {fake['upiId']} or call me at {fake['phoneNumber']} for immediate assistance.",
        ]

    elif scenario_id == "upi_fraud":
        return [
            # Turn 2
            f"To process your Rs 5000 cashback, please share your UPI ID. Our official support UPI is {fake['upiId']}.",
            # Turn 3
            f"If you face any issues, call our helpline {fake['phoneNumber']}. We are from official Paytm support team.",
            # Turn 4
            f"Just send Rs 10 to {fake['upiId']} as verification fee and your Rs 5000 will be credited within 5 minutes.",
            # Turn 5
            "This offer expires in 2 minutes. Please hurry and complete the verification.",
        ]

    elif scenario_id == "phishing_link":
        return [
            # Turn 2
            f"Click on {fake['phishingLink']} to claim your iPhone 15 Pro. This is a verified Amazon deal.",
            # Turn 3
            f"If the link doesn't work, email us at {fake['emailAddress']} and we'll send you a new link.",
            # Turn 4
            f"Don't miss out! Visit {fake['phishingLink']} before the timer runs out. Only 3 left in stock!",
            # Turn 5
            f"You can also contact us at {fake['emailAddress']} for any questions about your iPhone claim.",
        ]

    return ["Please respond quickly, this is urgent."] * 4


def build_conversation_history(
    scenario: dict,
    num_turns: int,
    agent_replies: list[str] | None = None,
) -> list[dict]:
    """
    Build a conversation history with alternating scammer/user messages.

    Args:
        scenario: Scenario dict with fakeData and initialMessage
        num_turns: Number of complete turn pairs (scammer + user)
        agent_replies: Optional list of agent replies. If None, uses placeholder.

    Returns:
        List of conversation message dicts suitable for AnalyzeRequest.conversationHistory
    """
    history = []
    followups = build_scammer_followups(scenario)
    base_time = datetime(2026, 1, 21, 10, 0, 0)

    for i in range(num_turns):
        # Scammer message
        if i == 0:
            scammer_text = scenario["initialMessage"]
        else:
            scammer_text = followups[min(i - 1, len(followups) - 1)]

        history.append({
            "sender": "scammer",
            "text": scammer_text,
            "timestamp": (base_time + timedelta(seconds=30 * (2 * i))).isoformat() + "Z",
        })

        # User (agent) reply
        reply = (
            agent_replies[i]
            if agent_replies and i < len(agent_replies)
            else "Oh no, what should I do? Please help me!"
        )
        history.append({
            "sender": "user",
            "text": reply,
            "timestamp": (base_time + timedelta(seconds=30 * (2 * i + 1))).isoformat() + "Z",
        })

    return history


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def client() -> TestClient:
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def api_key() -> str:
    return "test-api-key"


@pytest.fixture
def auth_headers() -> dict[str, str]:
    return {"x-api-key": "test-api-key"}


@pytest.fixture
def bank_fraud_scenario() -> dict:
    return BANK_FRAUD_SCENARIO.copy()


@pytest.fixture
def upi_fraud_scenario() -> dict:
    return UPI_FRAUD_SCENARIO.copy()


@pytest.fixture
def phishing_scenario() -> dict:
    return PHISHING_SCENARIO.copy()


@pytest.fixture
def all_scenarios() -> list[dict]:
    return [s.copy() for s in ALL_SCENARIOS]


@pytest.fixture
def sample_callback_payload() -> dict:
    """A sample GUVI callback payload (current broken version for baseline tests)."""
    return {
        "sessionId": "test-session-123",
        "scamDetected": True,
        "totalMessagesExchanged": 10,
        "extractedIntelligence": {
            "bankAccounts": ["1234567890123456"],
            "upiIds": ["scammer.fraud@fakebank"],
            "phishingLinks": [],
            "phoneNumbers": ["+91-9876543210"],
            "suspiciousKeywords": ["urgent", "blocked"],
        },
        "agentNotes": "Scammer used urgency tactics.",
    }


@pytest.fixture
def perfect_callback_payload() -> dict:
    """A perfect GUVI callback payload that should score 100/100 on bank_fraud."""
    return {
        "sessionId": "test-session-123",
        "status": "success",
        "scamDetected": True,
        "totalMessagesExchanged": 10,
        "extractedIntelligence": {
            "bankAccounts": ["1234567890123456"],
            "upiIds": ["scammer.fraud@fakebank"],
            "phoneNumbers": ["+91-9876543210"],
            "phishingLinks": [],
            "emailAddresses": [],
            "suspiciousKeywords": ["urgent", "blocked"],
        },
        "engagementMetrics": {
            "engagementDurationSeconds": 120,
            "totalMessagesExchanged": 10,
        },
        "agentNotes": "Scammer used urgency tactics and payment redirection.",
    }
