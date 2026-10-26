"""Seeded fake victim details the persona can hand to a scammer.

The seed comes from the conversation ID, so a scammer who asks twice gets the
same card, account and Aadhaar numbers.
"""

import hashlib
from typing import Any

from src.agents.fake_data import FakeDataGenerator


def build_fake_profile(conversation_id: str) -> dict[str, Any]:
    """Generate the full fake profile for one conversation."""
    # md5 only spreads conversation IDs into a stable seed; nothing relies on it for security.
    seed = int(hashlib.md5(conversation_id.encode(), usedforsecurity=False).hexdigest()[:8], 16)
    generator = FakeDataGenerator(seed=seed)

    credit_card = generator.generate_credit_card()
    card = credit_card.number
    bank_account = generator.generate_bank_account()
    persona_details = generator.generate_persona_details()

    return {
        "credit_card": credit_card,
        "bank_account": bank_account,
        "persona": persona_details,
        "otp": generator.generate_otp(),
        "aadhaar": generator.generate_aadhaar(),
        "pan": generator.generate_pan(),
        # Pre-formatted strings for easy use in prompts
        "card_number_formatted": f"{card[:4]} {card[4:8]} {card[8:12]} {card[12:]}",
        "card_number_raw": credit_card.number,
        "card_expiry": credit_card.expiry,
        "card_cvv": credit_card.cvv,
        "account_number": bank_account.number,
        "ifsc_code": bank_account.ifsc,
        "bank_name": bank_account.bank_name,
        "persona_name": persona_details.name,
        "persona_age": persona_details.age,
        "persona_address": persona_details.address,
        "customer_id": persona_details.customer_id,
    }


def format_fake_profile(fake_data: dict[str, Any]) -> str:
    """Render a profile as the bullet list the system prompt embeds."""
    card_type = fake_data["credit_card"].card_type
    return f"""- Credit Card: {fake_data["card_number_formatted"]} (type: {card_type})
- Card Expiry: {fake_data["card_expiry"]}
- Card CVV: {fake_data["card_cvv"]}
- Bank Account: {fake_data["account_number"]}
- IFSC Code: {fake_data["ifsc_code"]} ({fake_data["bank_name"]})
- OTP/Verification Code: {fake_data["otp"]}
- Aadhaar Number: {fake_data["aadhaar"]}
- PAN Card: {fake_data["pan"]}
- Your Name: {fake_data["persona_name"]}
- Your Age: {fake_data["persona_age"]}
- Your Address: {fake_data["persona_address"]}
- Customer ID: {fake_data["customer_id"]}"""
