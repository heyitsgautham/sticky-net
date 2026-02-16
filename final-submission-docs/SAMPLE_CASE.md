Sample Scenarios for Evaluation
For the Agentic Honey-Pot for Scam Detection & Intelligence Extraction problem, participants can use the following three representative scam scenarios to design, test, and evaluate their systems. These scenarios simulate common fraud patterns observed across Indian digital communication channels.
[
  {
    "scenarioId": "bank_fraud",
    "name": "Bank Fraud Detection",
    "description": "Bank account fraud with urgency tactics",
    "scamType": "bank_fraud",
    "initialMessage": "URGENT: Your SBI account has been compromised. Your account will be blocked in 2 hours. Share your account number and OTP immediately to verify your identity.",
    "metadata": {
      "channel": "SMS",
      "language": "English",
      "locale": "IN"
    },
    "weight": 10,
    "maxTurns": 10,
    "fakeData": {
      "bankAccount": "1234567890123456",
      "upiId": "scammer.fraud@fakebank",
      "phoneNumber": "+91-9876543210"
    }
  },
  {
    "scenarioId": "upi_fraud",
    "name": "UPI Fraud Multi-turn",
    "description": "UPI fraud with cashback scam",
    "scamType": "upi_fraud",
    "initialMessage": "Congratulations! You have won a cashback of Rs. 5000 from Paytm. To claim your reward, please verify your UPI details. This is from official customer support.",
    "metadata": {
      "channel": "WhatsApp",
      "language": "English",
      "locale": "IN"
    },
    "weight": 10,
    "maxTurns": 10,
    "fakeData": {
      "upiId": "cashback.scam@fakeupi",
      "phoneNumber": "+91-8765432109"
    }
  },
  {
    "scenarioId": "phishing_link",
    "name": "Phishing Link Detection",
    "description": "Phishing link with fake offer",
    "scamType": "phishing",
    "initialMessage": "You have been selected for iPhone 15 Pro at just Rs. 999! Click here to claim: http://amaz0n-deals.fake-site.com/claim?id=12345. Offer expires in 10 minutes!",
    "metadata": {
      "channel": "Email",
      "language": "English",
      "locale": "IN"
    },
    "weight": 10,
    "maxTurns": 10,
    "fakeData": {
      "phishingLink": "http://amaz0n-deals.fake-site.com/claim?id=12345",
      "emailAddress": "offers@fake-amazon-deals.com"
    }
  }
]


