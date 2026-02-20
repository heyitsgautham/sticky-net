"""
Fixtures for evaluation framework tests.
"""

import os
import pytest

# Ensure test env vars are set
os.environ.setdefault("API_KEY", "test-api-key")
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("ENVIRONMENT", "test")


@pytest.fixture
def perfect_bank_fraud_output():
    """A callback payload that should score 100/100 for bank fraud scenario."""
    return {
        "sessionId": "test-session-001",
        "status": "success",
        "scamDetected": True,
        "scamType": "bank_fraud",
        "confidenceLevel": 0.95,
        "totalMessagesExchanged": 20,
        "engagementDurationSeconds": 300,
        "extractedIntelligence": {
            "bankAccounts": ["50100487652341"],
            "upiIds": ["sbi.security@axisbank"],
            "phoneNumbers": ["+91-9823456710"],
            "phishingLinks": [],
            "emailAddresses": [],
        },
        "engagementMetrics": {
            "engagementDurationSeconds": 300,
            "totalMessagesExchanged": 20,
        },
        "agentNotes": "Detected bank fraud scam. Scammer impersonated SBI officer.",
    }


@pytest.fixture
def perfect_upi_fraud_output():
    """Payload for perfect UPI fraud scenario score."""
    return {
        "sessionId": "test-session-002",
        "status": "success",
        "scamDetected": True,
        "scamType": "upi_fraud",
        "confidenceLevel": 0.92,
        "totalMessagesExchanged": 18,
        "engagementDurationSeconds": 250,
        "extractedIntelligence": {
            "upiIds": ["paytm.rewards@oksbi"],
            "phoneNumbers": ["+91-8765049321"],
            "emailAddresses": ["support@paytm-rewards-official.com"],
            "bankAccounts": [],
            "phishingLinks": [],
        },
        "engagementMetrics": {
            "engagementDurationSeconds": 250,
            "totalMessagesExchanged": 18,
        },
        "agentNotes": "UPI cashback scam detected.",
    }


@pytest.fixture
def perfect_phishing_output():
    """Payload for perfect phishing scenario score."""
    return {
        "sessionId": "test-session-003",
        "status": "success",
        "scamDetected": True,
        "scamType": "phishing",
        "confidenceLevel": 0.90,
        "totalMessagesExchanged": 16,
        "engagementDurationSeconds": 200,
        "extractedIntelligence": {
            "phishingLinks": ["http://amaz0n-prime-deals.fakesite.com/claim?uid=78234"],
            "emailAddresses": ["deals@amaz0n-prime-offers.com"],
            "bankAccounts": [],
            "upiIds": [],
            "phoneNumbers": [],
        },
        "engagementMetrics": {
            "engagementDurationSeconds": 200,
            "totalMessagesExchanged": 16,
        },
        "agentNotes": "Phishing link detected.",
    }


@pytest.fixture
def good_agent_responses():
    """Agent responses that should score well on conversation quality."""
    return [
        "Oh no, that sounds very concerning! Can you tell me your name and which department you're calling from?",
        "I'm worried about my account. What is your employee ID so I can verify you're really from the bank?",
        "Before I share any details, can you tell me which branch office you're calling from? I want to call back to verify.",
        "I noticed you're asking for my OTP - isn't that suspicious? Why would a bank need my OTP to verify my account?",
        "Your request seems urgent but I've heard about scams like this. Can you provide your official phone number so I can call the bank directly?",
        "I'm concerned about this being a phishing attempt. The link you sent looks suspicious - why doesn't it use the official bank domain?",
        "You mentioned transferring money for verification. That sounds like a red flag. Legitimate banks don't ask for verification fees.",
        "Can you send me your official email address? I'd like to verify this through proper channels before proceeding.",
        "I've been speaking with you for a while now. Can you share your supervisor's contact number? I'd feel more comfortable verifying first.",
        "Thank you for your patience. Let me note down your UPI ID and account number one more time to make sure I have the right details.",
    ]


@pytest.fixture
def minimal_output():
    """A minimal output that should score low."""
    return {
        "scamDetected": False,
    }
