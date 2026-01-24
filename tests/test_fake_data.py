"""Tests for fake data generator module."""

import re

import pytest

from src.agents.fake_data import (
    FakeDataGenerator,
    FakeCreditCard,
    FakeBankAccount,
    FakePersona,
    get_fake_data_generator,
)


class TestFakeDataGenerator:
    """Tests for FakeDataGenerator class."""

    @pytest.fixture
    def generator(self) -> FakeDataGenerator:
        """Create generator with fixed seed for reproducibility."""
        return FakeDataGenerator(seed=42)

    @pytest.fixture
    def random_generator(self) -> FakeDataGenerator:
        """Create generator without seed for randomness tests."""
        return FakeDataGenerator()


class TestCreditCardGeneration(TestFakeDataGenerator):
    """Tests for credit card generation."""

    def test_generates_16_digit_number(self, generator: FakeDataGenerator):
        """Should generate 16-digit card numbers."""
        card = generator.generate_credit_card()
        assert len(card.number) == 16
        assert card.number.isdigit()

    def test_passes_luhn_validation(self, generator: FakeDataGenerator):
        """Generated cards should pass Luhn checksum."""
        for _ in range(10):
            card = generator.generate_credit_card()
            assert generator._validate_luhn(card.number), f"Failed Luhn: {card.number}"

    def test_generates_visa_card(self, generator: FakeDataGenerator):
        """Should generate Visa cards starting with 4."""
        card = generator.generate_credit_card(card_type="visa")
        assert card.number.startswith("4")
        assert card.card_type == "visa"

    def test_generates_mastercard(self, generator: FakeDataGenerator):
        """Should generate Mastercard starting with 5."""
        card = generator.generate_credit_card(card_type="mastercard")
        assert card.number.startswith("5")
        assert card.card_type == "mastercard"

    def test_generates_rupay_card(self, generator: FakeDataGenerator):
        """Should generate RuPay cards starting with 6."""
        card = generator.generate_credit_card(card_type="rupay")
        assert card.number.startswith("6")
        assert card.card_type == "rupay"

    def test_expiry_is_future_date(self, generator: FakeDataGenerator):
        """Expiry should be in the future."""
        card = generator.generate_credit_card()
        # Format: MM/YY
        assert re.match(r"\d{2}/\d{2}", card.expiry)
        month, year = card.expiry.split("/")
        assert 1 <= int(month) <= 12
        # Year should be >= 26 (current year)
        assert int(year) >= 26

    def test_cvv_is_3_digits(self, generator: FakeDataGenerator):
        """CVV should be 3 digits."""
        card = generator.generate_credit_card()
        assert len(card.cvv) == 3
        assert card.cvv.isdigit()
        assert 100 <= int(card.cvv) <= 999

    def test_to_dict_format(self, generator: FakeDataGenerator):
        """Should convert to correct dict format."""
        card = generator.generate_credit_card()
        data = card.to_dict()

        assert "number" in data
        assert "expiry" in data
        assert "cvv" in data
        assert "card_type" in data

    def test_uses_invalid_bins(self, generator: FakeDataGenerator):
        """Should use test/invalid BIN prefixes."""
        invalid_bins = (
            generator.INVALID_VISA_BINS +
            generator.INVALID_MASTERCARD_BINS +
            generator.INVALID_RUPAY_BINS
        )

        for _ in range(20):
            card = generator.generate_credit_card()
            bin_prefix = card.number[:6]
            assert bin_prefix in invalid_bins, f"Unexpected BIN: {bin_prefix}"

    def test_random_card_type_selection(self, random_generator: FakeDataGenerator):
        """Should randomly select card types when not specified."""
        card_types = set()
        for _ in range(50):
            card = random_generator.generate_credit_card()
            card_types.add(card.card_type)

        # Should have generated at least 2 different types
        assert len(card_types) >= 2


class TestLuhnAlgorithm(TestFakeDataGenerator):
    """Tests specifically for Luhn algorithm implementation."""

    def test_luhn_validates_known_valid_number(self, generator: FakeDataGenerator):
        """Should validate known valid card numbers."""
        # Known valid test numbers
        valid_numbers = [
            "4532015112830366",
            "5425233430109903",
            "4716108999716531",
        ]
        for number in valid_numbers:
            assert generator._validate_luhn(number), f"Should be valid: {number}"

    def test_luhn_rejects_invalid_number(self, generator: FakeDataGenerator):
        """Should reject invalid card numbers."""
        invalid_numbers = [
            "4532015112830367",  # Changed last digit
            "1234567890123456",  # Random
            "0000000000000000",  # All zeros
        ]
        for number in invalid_numbers:
            # Note: 0000000000000000 actually passes Luhn, but changed digits don't
            if number != "0000000000000000":
                assert not generator._validate_luhn(number), f"Should be invalid: {number}"

    def test_checksum_calculation(self, generator: FakeDataGenerator):
        """Should calculate correct check digit."""
        # For 453201511283036, check digit should be 6
        partial = "453201511283036"
        check = generator._luhn_checksum(partial)
        full = partial + check
        assert generator._validate_luhn(full)


class TestBankAccountGeneration(TestFakeDataGenerator):
    """Tests for bank account generation."""

    def test_generates_valid_length_account(self, generator: FakeDataGenerator):
        """Account number should be 11-16 digits."""
        account = generator.generate_bank_account()
        assert 11 <= len(account.number) <= 16
        assert account.number.isdigit()

    def test_generates_valid_ifsc_format(self, generator: FakeDataGenerator):
        """IFSC should match format AAAA0NNNNNN."""
        account = generator.generate_bank_account()
        # Format: 4 letters + 0 + 6 alphanumeric
        assert re.match(r"[A-Z]{4}0[0-9]{6}", account.ifsc)

    def test_generates_specific_bank(self, generator: FakeDataGenerator):
        """Should generate account for specified bank."""
        account = generator.generate_bank_account(bank="HDFC")
        assert account.ifsc.startswith("HDFC")
        assert account.bank_name == "HDFC Bank"

    def test_generates_sbi_by_default_for_unknown(self, generator: FakeDataGenerator):
        """Should fallback to SBI for unknown bank codes."""
        account = generator.generate_bank_account(bank="FAKE")
        assert account.ifsc.startswith("SBIN")
        assert account.bank_name == "State Bank of India"

    def test_account_starts_with_9(self, generator: FakeDataGenerator):
        """Account should start with 9 (invalid prefix)."""
        for _ in range(10):
            account = generator.generate_bank_account()
            assert account.number.startswith("9")

    def test_branch_code_starts_with_9(self, generator: FakeDataGenerator):
        """Branch code in IFSC should start with 9 (invalid)."""
        account = generator.generate_bank_account()
        branch_code = account.ifsc[5:]  # After BANK0
        assert branch_code.startswith("9")

    def test_includes_branch_info(self, generator: FakeDataGenerator):
        """Should include realistic branch information."""
        account = generator.generate_bank_account()
        assert account.branch  # Non-empty
        assert "," in account.branch  # Contains locality and city

    def test_to_dict_format(self, generator: FakeDataGenerator):
        """Should convert to correct dict format."""
        account = generator.generate_bank_account()
        data = account.to_dict()

        assert "number" in data
        assert "ifsc" in data
        assert "bank_name" in data
        assert "branch" in data


class TestPersonaGeneration(TestFakeDataGenerator):
    """Tests for persona generation."""

    def test_generates_full_name(self, generator: FakeDataGenerator):
        """Should generate first and last name."""
        persona = generator.generate_persona_details()
        assert " " in persona.name  # First and last name
        parts = persona.name.split()
        assert len(parts) == 2

    def test_generates_female_persona(self, generator: FakeDataGenerator):
        """Should generate female names when specified."""
        persona = generator.generate_persona_details(gender="female")
        first_name = persona.name.split()[0]
        assert first_name in generator.FEMALE_FIRST_NAMES

    def test_generates_male_persona(self, generator: FakeDataGenerator):
        """Should generate male names when specified."""
        persona = generator.generate_persona_details(gender="male")
        first_name = persona.name.split()[0]
        assert first_name in generator.MALE_FIRST_NAMES

    def test_generates_elderly_age(self, generator: FakeDataGenerator):
        """Age should be in elderly range (55-80)."""
        for _ in range(10):
            persona = generator.generate_persona_details()
            assert 55 <= persona.age <= 80

    def test_generates_customer_id(self, generator: FakeDataGenerator):
        """Should generate CUST-prefixed ID."""
        persona = generator.generate_persona_details()
        assert persona.customer_id.startswith("CUST")
        assert len(persona.customer_id) == 12  # CUST + 8 digits

    def test_generates_address_with_pincode(self, generator: FakeDataGenerator):
        """Address should include PIN code."""
        persona = generator.generate_persona_details()
        # PIN code pattern at end
        assert re.search(r"\d{6}$", persona.address)

    def test_to_dict_format(self, generator: FakeDataGenerator):
        """Should convert to correct dict format."""
        persona = generator.generate_persona_details()
        data = persona.to_dict()

        assert "name" in data
        assert "customer_id" in data
        assert "age" in data
        assert "address" in data


class TestOTPGeneration(TestFakeDataGenerator):
    """Tests for OTP generation."""

    def test_generates_6_digit_otp(self, generator: FakeDataGenerator):
        """Should generate 6-digit OTP by default."""
        otp = generator.generate_otp()
        assert len(otp) == 6
        assert otp.isdigit()

    def test_generates_custom_length_otp(self, generator: FakeDataGenerator):
        """Should generate OTP of specified length."""
        otp = generator.generate_otp(length=4)
        assert len(otp) == 4

        otp = generator.generate_otp(length=8)
        assert len(otp) == 8

    def test_avoids_obvious_patterns(self, random_generator: FakeDataGenerator):
        """Should not generate obvious patterns."""
        for _ in range(100):
            otp = random_generator.generate_otp()
            assert otp != "123456"
            assert otp != "654321"
            assert len(set(otp)) > 1  # Not all same digit


class TestAadhaarGeneration(TestFakeDataGenerator):
    """Tests for Aadhaar number generation."""

    def test_generates_12_digits(self, generator: FakeDataGenerator):
        """Should generate 12-digit Aadhaar."""
        aadhaar = generator.generate_aadhaar()
        assert len(aadhaar) == 12
        assert aadhaar.isdigit()

    def test_starts_with_valid_digit(self, generator: FakeDataGenerator):
        """Aadhaar should start with 2-9."""
        for _ in range(10):
            aadhaar = generator.generate_aadhaar()
            assert aadhaar[0] in "23456789"


class TestPANGeneration(TestFakeDataGenerator):
    """Tests for PAN generation."""

    def test_generates_valid_format(self, generator: FakeDataGenerator):
        """Should generate PAN in correct format."""
        pan = generator.generate_pan()
        assert len(pan) == 10
        # Format: AAAAA9999A
        assert re.match(r"[A-Z]{5}[0-9]{4}[A-Z]", pan)

    def test_fourth_char_is_p(self, generator: FakeDataGenerator):
        """Fourth character should be P (Individual)."""
        pan = generator.generate_pan()
        assert pan[3] == "P"


class TestSingletonPattern:
    """Tests for singleton generator access."""

    def test_get_generator_returns_instance(self):
        """Should return generator instance."""
        gen = get_fake_data_generator()
        assert isinstance(gen, FakeDataGenerator)

    def test_get_generator_with_seed(self):
        """Should create new instance with seed."""
        gen1 = get_fake_data_generator(seed=123)
        card1 = gen1.generate_credit_card()

        gen2 = get_fake_data_generator(seed=123)
        card2 = gen2.generate_credit_card()

        # Same seed should produce same output
        assert card1.number == card2.number


class TestReproducibility:
    """Tests for reproducible generation with seeds."""

    def test_same_seed_same_output(self):
        """Same seed should produce same output."""
        gen1 = FakeDataGenerator(seed=999)
        gen2 = FakeDataGenerator(seed=999)

        card1 = gen1.generate_credit_card()
        card2 = gen2.generate_credit_card()
        assert card1.number == card2.number

        account1 = gen1.generate_bank_account()
        account2 = gen2.generate_bank_account()
        assert account1.number == account2.number

        persona1 = gen1.generate_persona_details()
        persona2 = gen2.generate_persona_details()
        assert persona1.name == persona2.name

    def test_different_seeds_different_output(self):
        """Different seeds should produce different output."""
        gen1 = FakeDataGenerator(seed=111)
        gen2 = FakeDataGenerator(seed=222)

        card1 = gen1.generate_credit_card()
        card2 = gen2.generate_credit_card()
        assert card1.number != card2.number


class TestIntegration:
    """Integration tests for complete fake data scenarios."""

    def test_generate_complete_scam_response_data(self):
        """Should generate all data needed for scam response."""
        gen = FakeDataGenerator(seed=42)

        # Generate persona for the "victim"
        persona = gen.generate_persona_details(gender="female")
        assert persona.name
        assert persona.customer_id

        # Generate payment details
        card = gen.generate_credit_card()
        assert gen._validate_luhn(card.number)

        account = gen.generate_bank_account()
        assert account.ifsc

        # Generate verification data
        otp = gen.generate_otp()
        assert len(otp) == 6

        aadhaar = gen.generate_aadhaar()
        assert len(aadhaar) == 12

        pan = gen.generate_pan()
        assert len(pan) == 10

    def test_data_looks_realistic(self):
        """Generated data should look realistic."""
        gen = FakeDataGenerator()

        # Card should look like a real card
        card = gen.generate_credit_card(card_type="visa")
        assert card.number.startswith("4")  # Visa prefix
        assert len(card.number) == 16
        assert "/" in card.expiry

        # Bank account should look Indian
        account = gen.generate_bank_account(bank="SBIN")
        assert "State Bank" in account.bank_name
        assert account.ifsc.startswith("SBIN")

        # Persona should look like elderly Indian
        persona = gen.generate_persona_details()
        assert persona.age >= 55
        # Name should have Indian format
        assert any(
            name in persona.name
            for name in gen.LAST_NAMES
        )
