"""Extra scenarios for the extended suite: tech support and insurance scams."""

from __future__ import annotations

# ============================================================================
# SCENARIO 4: Tech Support Scam — Tests caseId + phone extraction
# ============================================================================

TECH_SUPPORT_SCENARIO = {
    "scenarioId": "tech_support_01",
    "name": "Microsoft Security Alert",
    "scamType": "tech_support_fraud",
    "weight": 30,
    "maxTurns": 10,
    "initialMessage": (
        "⚠️ CRITICAL ALERT: Your computer has been compromised with malware. "
        "Your personal data including bank details are being stolen. "
        "Call Microsoft Certified Support immediately to secure your system."
    ),
    "metadata": {"channel": "SMS", "language": "English", "locale": "IN"},
    "fakeData": {
        "phoneNumber": "+91-7890123456",
        "emailAddress": "techsupport@microsoft-help-india.com",
        "caseId": "MS-SEC-2026-78432",
    },
    "turns": [
        {
            "turn": 1,
            "scammer_message": (
                "⚠️ CRITICAL ALERT: Your computer has been compromised with malware. "
                "Your personal data including bank details are being stolen. "
                "Call Microsoft Certified Support immediately to secure your system."
            ),
            "expected_extractions": [],
        },
        {
            "turn": 2,
            "scammer_message": (
                "I am a Microsoft Certified Security Engineer. Your case has been assigned "
                "ID: MS-SEC-2026-78432. Please call us at +91-7890123456 for immediate "
                "remote assistance."
            ),
            "expected_extractions": ["MS-SEC-2026-78432", "+91-7890123456"],
        },
        {
            "turn": 3,
            "scammer_message": (
                "You can also email our security team at techsupport@microsoft-help-india.com. "
                "Your case MS-SEC-2026-78432 requires urgent action within the next hour."
            ),
            "expected_extractions": [
                "techsupport@microsoft-help-india.com",
                "MS-SEC-2026-78432",
            ],
        },
        {
            "turn": 4,
            "scammer_message": (
                "I can see your system is actively being attacked. The hackers are from "
                "Eastern Europe. We need to install protective software. Call +91-7890123456 now."
            ),
            "expected_extractions": ["+91-7890123456"],
        },
        {
            "turn": 5,
            "scammer_message": (
                "To fix this remotely, we need to install TeamViewer. The one-time "
                "security restoration fee is Rs 2,999. Email techsupport@microsoft-help-india.com "
                "for the payment link."
            ),
            "expected_extractions": ["techsupport@microsoft-help-india.com"],
        },
        {
            "turn": 6,
            "scammer_message": (
                "Your case MS-SEC-2026-78432 is being escalated to Level 3 support. "
                "Call +91-7890123456 within the next 15 minutes or your data will be lost."
            ),
            "expected_extractions": ["MS-SEC-2026-78432", "+91-7890123456"],
        },
        {
            "turn": 7,
            "scammer_message": (
                "We have helped over 10,000 customers today. Don't be the one who loses data. "
                "Contact: +91-7890123456 or techsupport@microsoft-help-india.com"
            ),
            "expected_extractions": ["+91-7890123456", "techsupport@microsoft-help-india.com"],
        },
        {
            "turn": 8,
            "scammer_message": (
                "All details for your reference - Case: MS-SEC-2026-78432, "
                "Phone: +91-7890123456, Email: techsupport@microsoft-help-india.com. "
                "Act immediately!"
            ),
            "expected_extractions": [
                "MS-SEC-2026-78432",
                "+91-7890123456",
                "techsupport@microsoft-help-india.com",
            ],
        },
        {
            "turn": 9,
            "scammer_message": (
                "This is the final escalation warning. Your Windows license will also "
                "be revoked if security check is not completed."
            ),
            "expected_extractions": [],
        },
        {
            "turn": 10,
            "scammer_message": (
                "Last chance: Call +91-7890123456 or email techsupport@microsoft-help-india.com. "
                "Case MS-SEC-2026-78432 will be closed as unresolved."
            ),
            "expected_extractions": [
                "+91-7890123456",
                "techsupport@microsoft-help-india.com",
                "MS-SEC-2026-78432",
            ],
        },
    ],
}


# ============================================================================
# SCENARIO 5: Insurance Scam — Tests policyNumber + phone + UPI
# ============================================================================

INSURANCE_SCAM_SCENARIO = {
    "scenarioId": "insurance_01",
    "name": "LIC Policy Expiry Scam",
    "scamType": "insurance_fraud",
    "weight": 30,
    "maxTurns": 10,
    "initialMessage": (
        "Dear Policyholder, your LIC policy is about to lapse due to unpaid premium. "
        "Pay immediately to avoid losing your coverage and maturity benefits. "
        "This is from LIC of India Head Office."
    ),
    "metadata": {"channel": "SMS", "language": "English", "locale": "IN"},
    "fakeData": {
        "policyNumber": "LIC-POL-827654321",
        "phoneNumber": "+91-9012345678",
        "upiId": "lic.premium@paytm",
    },
    "turns": [
        {
            "turn": 1,
            "scammer_message": (
                "Dear Policyholder, your LIC policy is about to lapse due to unpaid premium. "
                "Pay immediately to avoid losing your coverage and maturity benefits. "
                "This is from LIC of India Head Office."
            ),
            "expected_extractions": [],
        },
        {
            "turn": 2,
            "scammer_message": (
                "Your policy number LIC-POL-827654321 shows pending premium of Rs 12,500. "
                "If not paid within 24 hours, your policy will lapse permanently."
            ),
            "expected_extractions": ["LIC-POL-827654321"],
        },
        {
            "turn": 3,
            "scammer_message": (
                "For quick payment, use UPI: lic.premium@paytm. This is our official "
                "collection UPI ID. Payment reflects within 2 hours."
            ),
            "expected_extractions": ["lic.premium@paytm"],
        },
        {
            "turn": 4,
            "scammer_message": (
                "If you need help with payment, call our premium collection desk at "
                "+91-9012345678. Available between 9 AM to 6 PM."
            ),
            "expected_extractions": ["+91-9012345678"],
        },
        {
            "turn": 5,
            "scammer_message": (
                "Policy LIC-POL-827654321 has 6 hours left before lapse. "
                "Pay Rs 12,500 to lic.premium@paytm or call +91-9012345678."
            ),
            "expected_extractions": ["LIC-POL-827654321", "lic.premium@paytm", "+91-9012345678"],
        },
        {
            "turn": 6,
            "scammer_message": (
                "Your maturity amount of Rs 25,00,000 will be lost if policy LIC-POL-827654321 "
                "lapses. Think about your family's future!"
            ),
            "expected_extractions": ["LIC-POL-827654321"],
        },
        {
            "turn": 7,
            "scammer_message": (
                "We are processing bulk policy renewals. Pay to lic.premium@paytm now "
                "and get bonus coverage for 6 months FREE."
            ),
            "expected_extractions": ["lic.premium@paytm"],
        },
        {
            "turn": 8,
            "scammer_message": (
                "Complete reference: Policy LIC-POL-827654321, UPI lic.premium@paytm, "
                "Helpline +91-9012345678. Act before it's too late!"
            ),
            "expected_extractions": ["LIC-POL-827654321", "lic.premium@paytm", "+91-9012345678"],
        },
        {
            "turn": 9,
            "scammer_message": (
                "This is the final automated reminder. Your policy is in grace period. "
                "Once lapsed, revival will cost 3x the premium amount."
            ),
            "expected_extractions": [],
        },
        {
            "turn": 10,
            "scammer_message": (
                "LAST CHANCE: Pay to lic.premium@paytm or call +91-9012345678. "
                "Policy LIC-POL-827654321 expires in 30 minutes."
            ),
            "expected_extractions": ["lic.premium@paytm", "+91-9012345678", "LIC-POL-827654321"],
        },
    ],
}


# ============================================================================
# Scenario Registry
# ============================================================================
