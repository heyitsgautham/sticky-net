"""The three scenarios the hackathon scores: bank fraud, UPI fraud and phishing."""

from __future__ import annotations

# ============================================================================
# SCENARIO 1: Bank Fraud — High weight, tests bank account + UPI + phone
# ============================================================================

BANK_FRAUD_SCENARIO = {
    "scenarioId": "bank_fraud_01",
    "name": "SBI Account Compromise",
    "scamType": "bank_fraud",
    "weight": 35,
    "maxTurns": 10,
    "initialMessage": (
        "URGENT: Your SBI account has been compromised due to unauthorized login. "
        "Your account will be permanently blocked in 2 hours unless you verify "
        "your identity immediately. This is SBI Fraud Prevention Department."
    ),
    "metadata": {"channel": "SMS", "language": "English", "locale": "IN"},
    "fakeData": {
        "bankAccount": "50100487652341",
        "upiId": "sbi.security@axisbank",
        "phoneNumber": "+91-9823456710",
    },
    "turns": [
        {
            "turn": 1,
            "scammer_message": (
                "URGENT: Your SBI account has been compromised due to unauthorized login. "
                "Your account will be permanently blocked in 2 hours unless you verify "
                "your identity immediately. This is SBI Fraud Prevention Department."
            ),
            "expected_extractions": [],
        },
        {
            "turn": 2,
            "scammer_message": (
                "Sir/Madam, I am Senior Officer Rajesh Kumar from SBI Fraud Prevention Cell. "
                "We detected suspicious transactions on your account. For immediate assistance "
                "you can call me directly at +91-9823456710."
            ),
            "expected_extractions": ["+91-9823456710"],
        },
        {
            "turn": 3,
            "scammer_message": (
                "I understand your concern. To verify your identity and secure your account, "
                "please transfer Rs 1 as verification fee to our secure UPI: sbi.security@axisbank. "
                "This is a standard security procedure."
            ),
            "expected_extractions": ["sbi.security@axisbank"],
        },
        {
            "turn": 4,
            "scammer_message": (
                "If UPI is not available, you can transfer to our verification account. "
                "Account number: 50100487652341, IFSC: SBIN0001234, Name: SBI Security Cell. "
                "Just Rs 1 for verification."
            ),
            "expected_extractions": ["50100487652341"],
        },
        {
            "turn": 5,
            "scammer_message": (
                "Ma'am/Sir, time is running out. I have already extended the deadline for you. "
                "Send Rs 1 to UPI sbi.security@axisbank or account 50100487652341. "
                "Call me at +91-9823456710 if you face any issues."
            ),
            "expected_extractions": ["sbi.security@axisbank", "50100487652341", "+91-9823456710"],
        },
        {
            "turn": 6,
            "scammer_message": (
                "This is your final warning. Your account ending 4521 will be blocked permanently. "
                "Other customers have already verified. Don't lose your hard-earned money."
            ),
            "expected_extractions": [],
        },
        {
            "turn": 7,
            "scammer_message": (
                "I can see you are a valued customer with high balance. We are trying to protect you. "
                "Please send Rs 1 verification to sbi.security@axisbank from your UPI app."
            ),
            "expected_extractions": ["sbi.security@axisbank"],
        },
        {
            "turn": 8,
            "scammer_message": (
                "Let me give you all details again. Account: 50100487652341. UPI: sbi.security@axisbank. "
                "Contact: +91-9823456710. Verify within 30 minutes or your account is gone forever."
            ),
            "expected_extractions": ["50100487652341", "sbi.security@axisbank", "+91-9823456710"],
        },
        {
            "turn": 9,
            "scammer_message": (
                "I have escalated your case to the branch manager. One last chance — "
                "just complete the Rs 1 verification and your account will be safe."
            ),
            "expected_extractions": [],
        },
        {
            "turn": 10,
            "scammer_message": (
                "Your case has been marked as non-cooperative. RBI will be notified. "
                "Final option: transfer to 50100487652341 or UPI sbi.security@axisbank immediately."
            ),
            "expected_extractions": ["50100487652341", "sbi.security@axisbank"],
        },
    ],
}


# ============================================================================
# SCENARIO 2: UPI Fraud — Cashback/refund scam with UPI + phone
# ============================================================================

UPI_FRAUD_SCENARIO = {
    "scenarioId": "upi_fraud_01",
    "name": "Paytm Cashback Scam",
    "scamType": "upi_fraud",
    "weight": 35,
    "maxTurns": 10,
    "initialMessage": (
        "Congratulations! You have won Rs 5,000 cashback from Paytm Mega Rewards. "
        "To claim your reward, verify your account details. This is from official "
        "Paytm customer support team."
    ),
    "metadata": {"channel": "WhatsApp", "language": "English", "locale": "IN"},
    "fakeData": {
        "upiId": "paytm.rewards@oksbi",
        "phoneNumber": "+91-8765049321",
        "emailAddress": "support@paytm-rewards-official.com",
    },
    "turns": [
        {
            "turn": 1,
            "scammer_message": (
                "Congratulations! You have won Rs 5,000 cashback from Paytm Mega Rewards. "
                "To claim your reward, verify your account details. This is from official "
                "Paytm customer support team."
            ),
            "expected_extractions": [],
        },
        {
            "turn": 2,
            "scammer_message": (
                "Thank you for your interest! To process your Rs 5,000 cashback, "
                "please send Rs 10 processing fee to our official UPI: paytm.rewards@oksbi. "
                "Your cashback will be credited within 5 minutes."
            ),
            "expected_extractions": ["paytm.rewards@oksbi"],
        },
        {
            "turn": 3,
            "scammer_message": (
                "If you face any issues with UPI payment, you can contact our helpline "
                "at +91-8765049321. We are available 24/7 for Paytm reward claims."
            ),
            "expected_extractions": ["+91-8765049321"],
        },
        {
            "turn": 4,
            "scammer_message": (
                "I can see your reward is about to expire! Only 3 minutes left. "
                "Send Rs 10 to paytm.rewards@oksbi right now. This is one-time offer."
            ),
            "expected_extractions": ["paytm.rewards@oksbi"],
        },
        {
            "turn": 5,
            "scammer_message": (
                "You can also email us at support@paytm-rewards-official.com for any queries. "
                "But please hurry, the reward expires soon! UPI: paytm.rewards@oksbi"
            ),
            "expected_extractions": ["support@paytm-rewards-official.com", "paytm.rewards@oksbi"],
        },
        {
            "turn": 6,
            "scammer_message": (
                "Many customers have already claimed their cashback today. "
                "Don't miss out! Call +91-8765049321 if you need help with the process."
            ),
            "expected_extractions": ["+91-8765049321"],
        },
        {
            "turn": 7,
            "scammer_message": (
                "I have extended your claim window by 5 more minutes as a special favor. "
                "Just pay Rs 10 to paytm.rewards@oksbi and you get Rs 5000 back."
            ),
            "expected_extractions": ["paytm.rewards@oksbi"],
        },
        {
            "turn": 8,
            "scammer_message": (
                "This is your absolute last chance. Contact details once more: "
                "UPI: paytm.rewards@oksbi, Phone: +91-8765049321, "
                "Email: support@paytm-rewards-official.com"
            ),
            "expected_extractions": [
                "paytm.rewards@oksbi",
                "+91-8765049321",
                "support@paytm-rewards-official.com",
            ],
        },
        {
            "turn": 9,
            "scammer_message": (
                "Your reward ID PYT-CLAIM-8827 will expire permanently. "
                "After that you cannot claim this amount ever."
            ),
            "expected_extractions": [],
        },
        {
            "turn": 10,
            "scammer_message": (
                "Final notification: Send Rs 10 to paytm.rewards@oksbi or call +91-8765049321. "
                "After this your reward is cancelled and cannot be recovered."
            ),
            "expected_extractions": ["paytm.rewards@oksbi", "+91-8765049321"],
        },
    ],
}


# ============================================================================
# SCENARIO 3: Phishing — Fake website + email extraction
# ============================================================================

PHISHING_SCENARIO = {
    "scenarioId": "phishing_01",
    "name": "Amazon Prize Phishing",
    "scamType": "phishing",
    "weight": 30,
    "maxTurns": 10,
    "initialMessage": (
        "Dear Customer, you have been selected for an exclusive Amazon Prime deal! "
        "Get iPhone 15 Pro for just Rs 999. Limited stock. Click here to claim: "
        "http://amaz0n-prime-deals.fakesite.com/claim?uid=78234"
    ),
    "metadata": {"channel": "Email", "language": "English", "locale": "IN"},
    "fakeData": {
        "phishingLink": "http://amaz0n-prime-deals.fakesite.com/claim?uid=78234",
        "emailAddress": "deals@amaz0n-prime-offers.com",
    },
    "turns": [
        {
            "turn": 1,
            "scammer_message": (
                "Dear Customer, you have been selected for an exclusive Amazon Prime deal! "
                "Get iPhone 15 Pro for just Rs 999. Limited stock. Click here to claim: "
                "http://amaz0n-prime-deals.fakesite.com/claim?uid=78234"
            ),
            "expected_extractions": ["http://amaz0n-prime-deals.fakesite.com/claim?uid=78234"],
        },
        {
            "turn": 2,
            "scammer_message": (
                "Thank you for showing interest! This is a verified Amazon partner deal. "
                "Visit http://amaz0n-prime-deals.fakesite.com/claim?uid=78234 to complete "
                "your purchase. Only 5 units remaining!"
            ),
            "expected_extractions": ["http://amaz0n-prime-deals.fakesite.com/claim?uid=78234"],
        },
        {
            "turn": 3,
            "scammer_message": (
                "If the link doesn't work, please email us at deals@amaz0n-prime-offers.com "
                "and we will send you a new claim link. We are official Amazon partner."
            ),
            "expected_extractions": ["deals@amaz0n-prime-offers.com"],
        },
        {
            "turn": 4,
            "scammer_message": (
                "Many winners have already claimed their iPhones today! Check our website: "
                "http://amaz0n-prime-deals.fakesite.com/claim?uid=78234 for live updates."
            ),
            "expected_extractions": ["http://amaz0n-prime-deals.fakesite.com/claim?uid=78234"],
        },
        {
            "turn": 5,
            "scammer_message": (
                "You can reach our customer support at deals@amaz0n-prime-offers.com any time. "
                "But the deal closes in 10 minutes. Click the link now!"
            ),
            "expected_extractions": ["deals@amaz0n-prime-offers.com"],
        },
        {
            "turn": 6,
            "scammer_message": (
                "This is an exclusive offer only for selected Prime members like you. "
                "Claim here: http://amaz0n-prime-deals.fakesite.com/claim?uid=78234"
            ),
            "expected_extractions": ["http://amaz0n-prime-deals.fakesite.com/claim?uid=78234"],
        },
        {
            "turn": 7,
            "scammer_message": (
                "Timer is almost up! Don't miss this once-in-a-lifetime deal. "
                "Email deals@amaz0n-prime-offers.com or click the link immediately!"
            ),
            "expected_extractions": ["deals@amaz0n-prime-offers.com"],
        },
        {
            "turn": 8,
            "scammer_message": (
                "Final reminder: Claim your iPhone 15 Pro at "
                "http://amaz0n-prime-deals.fakesite.com/claim?uid=78234. "
                "Contact: deals@amaz0n-prime-offers.com. Only 1 left!"
            ),
            "expected_extractions": [
                "http://amaz0n-prime-deals.fakesite.com/claim?uid=78234",
                "deals@amaz0n-prime-offers.com",
            ],
        },
        {
            "turn": 9,
            "scammer_message": (
                "We are closing this offer now. You were so close! "
                "Last chance at http://amaz0n-prime-deals.fakesite.com/claim?uid=78234"
            ),
            "expected_extractions": ["http://amaz0n-prime-deals.fakesite.com/claim?uid=78234"],
        },
        {
            "turn": 10,
            "scammer_message": (
                "Offer closed. But we can reopen for you if you act in 2 minutes. "
                "Email deals@amaz0n-prime-offers.com immediately to request extension."
            ),
            "expected_extractions": ["deals@amaz0n-prime-offers.com"],
        },
    ],
}
