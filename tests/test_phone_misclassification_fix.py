#!/usr/bin/env python3
"""
Test to verify that the phone number misclassification bug is fixed.

Bug: Phone numbers like 919123456789 (12 digits with country code) were being
classified as bank accounts instead of phone numbers.

Fix: Added _looks_like_phone() method to detect and filter out phone numbers
before classifying them as bank accounts.
"""

from src.intelligence.extractor import IntelligenceExtractor


def test_12_digit_phone_with_country_code():
    """Test that 919123456789 is classified as PHONE, not BANK_ACCOUNT."""
    extractor = IntelligenceExtractor()
    
    # The problematic case from convo-3
    text = "Call me at 919123456789"
    result = extractor.extract(text)
    
    print("\n" + "="*70)
    print("TEST: 12-digit phone with country code prefix (919123456789)")
    print("="*70)
    print(f"Text: {text}")
    print(f"Extracted phone_numbers: {result.phone_numbers}")
    print(f"Extracted bank_accounts: {result.bank_accounts}")
    
    # Should be in phone_numbers, NOT in bank_accounts
    assert "919123456789" in result.phone_numbers, \
        f"Expected 919123456789 in phone_numbers, got {result.phone_numbers}"
    assert "919123456789" not in result.bank_accounts, \
        f"BUG NOT FIXED: 919123456789 still in bank_accounts! {result.bank_accounts}"
    
    print("✓ PASS: Correctly classified as phone number")


def test_10_digit_phone():
    """Test that 10-digit phones are still extracted correctly."""
    extractor = IntelligenceExtractor()
    
    text = "Call me on 9876543210"
    result = extractor.extract(text)
    
    print("\n" + "="*70)
    print("TEST: 10-digit phone number (9876543210)")
    print("="*70)
    print(f"Text: {text}")
    print(f"Extracted phone_numbers: {result.phone_numbers}")
    print(f"Extracted bank_accounts: {result.bank_accounts}")
    
    assert "9876543210" in result.phone_numbers, \
        f"Expected 9876543210 in phone_numbers, got {result.phone_numbers}"
    assert "9876543210" not in result.bank_accounts, \
        f"Unexpected: 9876543210 in bank_accounts"
    
    print("✓ PASS: 10-digit phone correctly classified")


def test_legitimate_bank_account_not_phone():
    """Test that legitimate bank accounts are NOT filtered out."""
    extractor = IntelligenceExtractor()
    
    # Real bank accounts that don't look like phones
    text = "Transfer to account 12345678901234 or 98765432101234"
    result = extractor.extract(text)
    
    print("\n" + "="*70)
    print("TEST: Legitimate bank accounts (not phone numbers)")
    print("="*70)
    print(f"Text: {text}")
    print(f"Extracted bank_accounts: {result.bank_accounts}")
    print(f"Extracted phone_numbers: {result.phone_numbers}")
    
    # 12345678901234 - doesn't start with 6,7,8,9 so not a phone
    assert "12345678901234" in result.bank_accounts, \
        f"Expected 12345678901234 in bank_accounts, got {result.bank_accounts}"
    
    # 98765432101234 - 14 digits, even if starts with 9, it's too long for a phone
    assert "98765432101234" in result.bank_accounts, \
        f"Expected 98765432101234 in bank_accounts, got {result.bank_accounts}"
    
    print("✓ PASS: Legitimate bank accounts preserved")


def test_mixed_scenario():
    """Test a realistic scenario with mixed data types."""
    extractor = IntelligenceExtractor()
    
    text = """
    Send Rs. 5000 to A/C: 12345678901234
    Or call 919876543210
    UPI: scammer@ybl
    Backup number: 9876543210
    """
    result = extractor.extract(text)
    
    print("\n" + "="*70)
    print("TEST: Mixed scenario with multiple data types")
    print("="*70)
    print(f"Extracted bank_accounts: {result.bank_accounts}")
    print(f"Extracted phone_numbers: {result.phone_numbers}")
    print(f"Extracted upi_ids: {result.upi_ids}")
    
    # Check bank accounts
    assert "12345678901234" in result.bank_accounts, \
        "Expected bank account 12345678901234"
    assert "919876543210" not in result.bank_accounts, \
        "BUG: 919876543210 should NOT be in bank_accounts (it's a phone!)"
    
    # Check phones
    assert "919876543210" in result.phone_numbers, \
        "Expected phone 919876543210"
    assert "9876543210" in result.phone_numbers, \
        "Expected phone 9876543210"
    
    # Check UPI
    assert "scammer@ybl" in result.upi_ids, \
        "Expected UPI scammer@ybl"
    
    print("✓ PASS: All data types correctly classified")


def test_edge_cases():
    """Test edge cases for phone number detection."""
    extractor = IntelligenceExtractor()
    
    test_cases = [
        ("919123456789", ["919123456789"], "12 digits with 91 prefix, starts with 6-9"),
        ("+919876543210", ["+919876543210", "919876543210"], "+91 prefix (both forms extracted)"),
        ("6123456789", ["6123456789"], "10 digits starting with 6"),
        ("7123456789", ["7123456789"], "10 digits starting with 7"),
        ("8123456789", ["8123456789"], "10 digits starting with 8"),
        ("9123456789", ["9123456789"], "10 digits starting with 9"),
        ("5123456789", [], "10 digits starting with 5 (invalid phone)"),
    ]
    
    print("\n" + "="*70)
    print("TEST: Edge cases for phone number detection")
    print("="*70)
    
    for number, expected_phones, description in test_cases:
        text = f"Call me at {number}"
        result = extractor.extract(text)
        
        # Normalize expected for comparison
        extracted = set(result.phone_numbers)
        expected = set(expected_phones)
        
        print(f"\n  {description}")
        print(f"  Input:    {number}")
        print(f"  Expected: {expected}")
        print(f"  Got:      {extracted}")
        
        if extracted == expected:
            print(f"  ✓ PASS")
        else:
            print(f"  ✗ FAIL")
            raise AssertionError(
                f"Phone detection failed for {description}. "
                f"Expected {expected}, got {extracted}"
            )


if __name__ == "__main__":
    print("\n" + "="*70)
    print("PHONE NUMBER MISCLASSIFICATION FIX VERIFICATION")
    print("="*70)
    
    try:
        test_12_digit_phone_with_country_code()
        test_10_digit_phone()
        test_legitimate_bank_account_not_phone()
        test_mixed_scenario()
        test_edge_cases()
        
        print("\n" + "="*70)
        print("✓ ALL TESTS PASSED - BUG IS FIXED!")
        print("="*70)
        print("\nSummary:")
        print("  • 919123456789 correctly classified as PHONE, not bank account")
        print("  • 10-digit phones still work correctly")
        print("  • Bank accounts not starting with 6-9 are preserved")
        print("  • Edge cases handled properly")
        
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        raise
