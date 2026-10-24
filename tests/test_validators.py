"""Tests for the intelligence validators that filter LLM and regex extractions."""

import pytest

from src.intelligence.validators import (
    BENEFICIARY_NAME_BLOCKLIST,
    is_suspicious_url,
    validate_bank_account,
    validate_beneficiary_name,
    validate_email,
    validate_extraction_result,
    validate_ifsc,
    validate_phone_number,
    validate_upi_id,
    validate_url,
)


@pytest.mark.parametrize(
    ("phone", "valid"),
    [
        ("9876543210", True),
        ("+91 98765 43210", True),
        ("+91-9876543210", True),
        ("919876543210", True),
        ("5876543210", False),  # Indian mobiles start with 6-9
        ("98765", False),
        ("", False),
    ],
)
def test_validate_phone_number(phone: str, valid: bool) -> None:
    assert validate_phone_number(phone) is valid


@pytest.mark.parametrize(
    ("upi", "valid"),
    [
        ("fraud@okaxis", True),
        ("Fraud@YBL", True),
        ("a@b", False),
        ("noat", False),
        ("x@abcdefghijklmnopq", False),  # provider part longer than 15 letters
        ("name@gmail.com", False),  # an email, not a UPI handle
    ],
)
def test_validate_upi_id(upi: str, valid: bool) -> None:
    assert validate_upi_id(upi) is valid


@pytest.mark.parametrize(
    ("account", "valid"),
    [
        ("123456789012", True),
        ("1234 5678 9012", True),
        ("9182736450129876", True),
        ("12345678", False),  # under 9 digits
        ("1111111111", False),  # one repeated digit
        ("9876543210", False),  # a mobile number, not an account
        ("", False),
    ],
)
def test_validate_bank_account(account: str, valid: bool) -> None:
    assert validate_bank_account(account) is valid


@pytest.mark.parametrize(
    ("ifsc", "valid"),
    [
        ("SBIN0001234", True),
        ("sbin0001234", True),
        ("SBIN1001234", False),  # fifth character must be 0
        ("SBIN000123", False),
    ],
)
def test_validate_ifsc(ifsc: str, valid: bool) -> None:
    assert validate_ifsc(ifsc) is valid


@pytest.mark.parametrize(
    ("url", "valid"),
    [
        ("http://bit.ly/abc", True),
        ("sbi-kyc-update.com/verify", True),
        ("http://secure-banking-verify.fake-site.com/login?ref=abc", True),
        ("https://www.google.com", False),  # valid URL, nothing suspicious
        ("https://example.com.", False),
        ("hello", False),
        ("", False),
    ],
)
def test_validate_url_keeps_only_suspicious_links(url: str, valid: bool) -> None:
    assert validate_url(url) is valid


def test_is_suspicious_url_matches_shorteners_case_insensitively() -> None:
    assert is_suspicious_url("HTTPS://BIT.LY/claim")
    assert not is_suspicious_url("https://www.wikipedia.org")


@pytest.mark.parametrize(
    ("email", "valid"),
    [
        ("support@secure-banking-verify.com", True),
        ("a@okaxis.com", False),  # okaxis is a UPI provider, so this is a UPI handle
        ("no-at.com", False),
        ("x@y", False),
    ],
)
def test_validate_email(email: str, valid: bool) -> None:
    assert validate_email(email) is valid


@pytest.mark.parametrize(
    "name", ["Rahul Kumar", "Priya Singh", "Amit Sharma", "Sanjay Patel", "O'Brien Singh"]
)
def test_validate_beneficiary_name_accepts_real_names(name: str) -> None:
    assert validate_beneficiary_name(name)


@pytest.mark.parametrize(
    "name",
    [
        "Now",
        "Before Paying",
        "Name",
        "Pay Now",
        "Send Money",
        "Bank Transfer",
        "Dear Customer",
        "Ram",  # one short word is more likely noise than a name
        "R2D2",
        "A" * 60,
        "",
    ],
)
def test_validate_beneficiary_name_rejects_false_positives(name: str) -> None:
    assert not validate_beneficiary_name(name)


def test_blocklist_holds_lowercase_words() -> None:
    assert BENEFICIARY_NAME_BLOCKLIST
    assert all(word == word.lower() for word in BENEFICIARY_NAME_BLOCKLIST)


def test_validate_extraction_result_filters_and_normalises() -> None:
    result = validate_extraction_result(
        {
            "bank_accounts": ["1234-5678-9012", "9876543210"],
            "upi_ids": ["Fraud@YBL"],
            "phone_numbers": ["+91 98765 43210", "123"],
            "urls": ["http://bit.ly/x.", "https://www.google.com"],
            "emails": ["A@Fake.com"],
            "beneficiary_names": ["rajesh kumar", "Now"],
            "bank_names": [" SBI ", ""],
            "ifsc_codes": ["sbin0001234"],
            "whatsapp_numbers": ["919876543210"],
        }
    )

    assert result == {
        "bank_accounts": ["123456789012"],
        "upi_ids": ["fraud@ybl"],
        "phone_numbers": ["9876543210"],
        "urls": ["http://bit.ly/x"],
        "emails": ["a@fake.com"],
        "beneficiary_names": ["Rajesh Kumar"],
        "bank_names": ["SBI"],
        "ifsc_codes": ["SBIN0001234"],
        "whatsapp_numbers": ["9876543210"],
    }


def test_validate_extraction_result_tolerates_missing_and_null_fields() -> None:
    result = validate_extraction_result({"bank_accounts": None})
    assert all(values == [] for values in result.values())
    assert len(result) == 9
