"""Fake data generator for honeypot engagement.

Generates believable but invalid financial data to:
1. Buy time while scammer types/processes data
2. Force errors that reveal scammer infrastructure
3. Maintain credibility as a compliant but confused victim
"""

import random
import string
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any


@dataclass
class FakeCreditCard:
    """Fake credit card data."""

    number: str
    expiry: str
    cvv: str
    card_type: str

    def to_dict(self) -> dict[str, str]:
        """Convert to dictionary."""
        return {
            "number": self.number,
            "expiry": self.expiry,
            "cvv": self.cvv,
            "card_type": self.card_type,
        }


@dataclass
class FakeBankAccount:
    """Fake bank account data."""

    number: str
    ifsc: str
    bank_name: str
    branch: str

    def to_dict(self) -> dict[str, str]:
        """Convert to dictionary."""
        return {
            "number": self.number,
            "ifsc": self.ifsc,
            "bank_name": self.bank_name,
            "branch": self.branch,
        }


@dataclass
class FakePersona:
    """Fake persona details."""

    name: str
    customer_id: str
    age: int
    address: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "customer_id": self.customer_id,
            "age": self.age,
            "address": self.address,
        }


class FakeDataGenerator:
    """
    Generate believable but invalid financial data.

    The data is designed to:
    - Pass basic format validation (Luhn checksum, etc.)
    - Fail when actually processed (invalid BINs, non-existent accounts)
    - Waste scammer time while appearing legitimate
    """

    # Invalid BIN prefixes that look real but won't work
    # These are fictional prefixes that resemble real card patterns
    INVALID_VISA_BINS = [
        "400000",  # Test BIN
        "411111",  # Test BIN
        "400012",  # Invalid
        "400023",  # Invalid
        "499999",  # Invalid
    ]

    INVALID_MASTERCARD_BINS = [
        "510000",  # Test BIN
        "520000",  # Test BIN
        "540000",  # Test BIN
        "559999",  # Invalid
    ]

    INVALID_RUPAY_BINS = [
        "607000",  # Invalid RuPay-like
        "608000",  # Invalid RuPay-like
        "652000",  # Invalid RuPay-like
    ]

    # Indian bank IFSC prefixes (real banks, but fake branch codes)
    BANK_IFSC_PREFIXES = {
        "SBIN": "State Bank of India",
        "HDFC": "HDFC Bank",
        "ICIC": "ICICI Bank",
        "PUNB": "Punjab National Bank",
        "BARB": "Bank of Baroda",
        "CNRB": "Canara Bank",
        "UBIN": "Union Bank of India",
        "BKID": "Bank of India",
        "KKBK": "Kotak Mahindra Bank",
        "UTIB": "Axis Bank",
    }

    # Elderly Indian names (typical of scam targets)
    FEMALE_FIRST_NAMES = [
        "Kamala", "Lakshmi", "Saraswati", "Parvati", "Sita",
        "Radha", "Durga", "Ganga", "Savitri", "Shakuntala",
        "Meena", "Saroj", "Sumitra", "Pushpa", "Shanti",
        "Kausalya", "Urmila", "Sunita", "Annapurna", "Vimala",
    ]

    MALE_FIRST_NAMES = [
        "Ramesh", "Suresh", "Rajesh", "Mahesh", "Ganesh",
        "Prakash", "Satish", "Girish", "Harish", "Dinesh",
        "Mohan", "Sohan", "Rohan", "Kishan", "Shyam",
        "Gopal", "Balram", "Raghunath", "Jagdish", "Devendra",
    ]

    LAST_NAMES = [
        "Sharma", "Verma", "Gupta", "Singh", "Kumar",
        "Patel", "Devi", "Rao", "Reddy", "Nair",
        "Pillai", "Menon", "Iyer", "Iyengar", "Agarwal",
        "Joshi", "Pandey", "Mishra", "Dubey", "Tiwari",
    ]

    # Indian cities for addresses
    CITIES = [
        ("Mumbai", "Maharashtra"),
        ("Delhi", "Delhi"),
        ("Bangalore", "Karnataka"),
        ("Chennai", "Tamil Nadu"),
        ("Kolkata", "West Bengal"),
        ("Hyderabad", "Telangana"),
        ("Pune", "Maharashtra"),
        ("Ahmedabad", "Gujarat"),
        ("Jaipur", "Rajasthan"),
        ("Lucknow", "Uttar Pradesh"),
        ("Patna", "Bihar"),
        ("Bhopal", "Madhya Pradesh"),
        ("Indore", "Madhya Pradesh"),
        ("Nagpur", "Maharashtra"),
        ("Varanasi", "Uttar Pradesh"),
    ]

    LOCALITIES = [
        "Gandhi Nagar", "Nehru Colony", "Rajiv Chowk", "MG Road",
        "Civil Lines", "Sadar Bazaar", "Station Road", "Bank Colony",
        "Teachers Colony", "Government Quarters", "Old City",
        "Cantonment Area", "University Road", "Temple Street",
    ]

    def __init__(self, seed: int | None = None) -> None:
        """
        Initialize generator with optional seed for reproducibility.

        Args:
            seed: Random seed for reproducible generation
        """
        self.rng = random.Random(seed)

    def _luhn_checksum(self, partial_number: str) -> str:
        """
        Calculate Luhn checksum digit for a partial card number.

        The Luhn algorithm:
        1. From right to left, double every second digit
        2. If doubling results in > 9, subtract 9
        3. Sum all digits
        4. Check digit makes sum divisible by 10

        Args:
            partial_number: Card number without check digit (15 digits for 16-digit card)

        Returns:
            Single check digit that makes the full number pass Luhn validation
        """
        digits = [int(d) for d in partial_number]
        # For a 15-digit partial, we need to double starting from the last digit
        # (which will be at even index 0 from the right in the final 16-digit number)
        for i in range(len(digits) - 1, -1, -2):
            digits[i] *= 2
            if digits[i] > 9:
                digits[i] -= 9

        total = sum(digits)
        check_digit = (10 - (total % 10)) % 10
        return str(check_digit)

    def _validate_luhn(self, number: str) -> bool:
        """
        Validate a number against Luhn algorithm.

        Args:
            number: Full card number to validate

        Returns:
            True if passes Luhn checksum
        """
        digits = [int(d) for d in number]
        # Double every second digit from right (starting at index -2)
        for i in range(len(digits) - 2, -1, -2):
            digits[i] *= 2
            if digits[i] > 9:
                digits[i] -= 9

        return sum(digits) % 10 == 0

    def generate_credit_card(self, card_type: str | None = None) -> FakeCreditCard:
        """
        Generate a fake credit card that passes Luhn validation.

        The card number will:
        - Pass Luhn checksum validation (looks legitimate)
        - Use invalid/test BIN prefixes (will fail when charged)
        - Have realistic expiry dates and CVV

        Args:
            card_type: Optional type ("visa", "mastercard", "rupay"). Random if None.

        Returns:
            FakeCreditCard with number, expiry, cvv, and card_type
        """
        if card_type is None:
            card_type = self.rng.choice(["visa", "mastercard", "rupay"])

        card_type = card_type.lower()

        # Select BIN based on card type
        if card_type == "visa":
            bin_prefix = self.rng.choice(self.INVALID_VISA_BINS)
        elif card_type == "mastercard":
            bin_prefix = self.rng.choice(self.INVALID_MASTERCARD_BINS)
        elif card_type == "rupay":
            bin_prefix = self.rng.choice(self.INVALID_RUPAY_BINS)
        else:
            bin_prefix = self.rng.choice(self.INVALID_VISA_BINS)
            card_type = "visa"

        # Generate remaining digits (need 15 total for 16-digit card, minus BIN length)
        remaining_length = 15 - len(bin_prefix)
        middle_digits = "".join(
            str(self.rng.randint(0, 9)) for _ in range(remaining_length)
        )

        partial_number = bin_prefix + middle_digits
        check_digit = self._luhn_checksum(partial_number)
        full_number = partial_number + check_digit

        # Generate expiry (1-4 years in future)
        future_months = self.rng.randint(12, 48)
        expiry_date = datetime.now() + timedelta(days=future_months * 30)
        expiry = expiry_date.strftime("%m/%y")

        # Generate CVV (3 digits, avoid obvious patterns)
        cvv = str(self.rng.randint(100, 999))

        return FakeCreditCard(
            number=full_number,
            expiry=expiry,
            cvv=cvv,
            card_type=card_type,
        )

    def generate_bank_account(self, bank: str | None = None) -> FakeBankAccount:
        """
        Generate a fake Indian bank account.

        The account will:
        - Have realistic format (9-18 digits)
        - Use real bank IFSC prefixes with fake branch codes
        - Look legitimate but not correspond to real accounts

        Args:
            bank: Optional bank code (e.g., "SBIN", "HDFC"). Random if None.

        Returns:
            FakeBankAccount with number, ifsc, bank_name, and branch
        """
        if bank is None:
            bank = self.rng.choice(list(self.BANK_IFSC_PREFIXES.keys()))

        bank = bank.upper()
        if bank not in self.BANK_IFSC_PREFIXES:
            bank = "SBIN"

        bank_name = self.BANK_IFSC_PREFIXES[bank]

        # Generate IFSC: BANK0 + 6 digits (0 is standard separator)
        # Use 9 as first digit after 0 to indicate fake branch
        branch_code = "9" + "".join(str(self.rng.randint(0, 9)) for _ in range(5))
        ifsc = f"{bank}0{branch_code}"

        # Generate account number (11-16 digits typical for Indian banks)
        account_length = self.rng.randint(11, 16)
        # Start with 9 to indicate test/invalid account
        account_number = "9" + "".join(
            str(self.rng.randint(0, 9)) for _ in range(account_length - 1)
        )

        # Fake branch name
        city, state = self.rng.choice(self.CITIES)
        locality = self.rng.choice(self.LOCALITIES)
        branch = f"{locality}, {city}"

        return FakeBankAccount(
            number=account_number,
            ifsc=ifsc,
            bank_name=bank_name,
            branch=branch,
        )

    def generate_persona_details(self, gender: str | None = None) -> FakePersona:
        """
        Generate fake elderly Indian persona details.

        The persona is designed to:
        - Appear as typical scam target (elderly, trusting)
        - Have realistic but fake identifying information
        - Support the honeypot's confused victim act

        Args:
            gender: Optional "male" or "female". Random if None.

        Returns:
            FakePersona with name, customer_id, age, and address
        """
        if gender is None:
            gender = self.rng.choice(["male", "female"])

        gender = gender.lower()

        # Generate name
        if gender == "female":
            first_name = self.rng.choice(self.FEMALE_FIRST_NAMES)
        else:
            first_name = self.rng.choice(self.MALE_FIRST_NAMES)

        last_name = self.rng.choice(self.LAST_NAMES)
        full_name = f"{first_name} {last_name}"

        # Generate age (elderly: 55-80)
        age = self.rng.randint(55, 80)

        # Generate customer ID (looks like bank customer ID)
        customer_id = "CUST" + "".join(str(self.rng.randint(0, 9)) for _ in range(8))

        # Generate address
        house_number = self.rng.randint(1, 500)
        locality = self.rng.choice(self.LOCALITIES)
        city, state = self.rng.choice(self.CITIES)
        pin_code = str(self.rng.randint(100000, 999999))
        address = f"{house_number}, {locality}, {city}, {state} - {pin_code}"

        return FakePersona(
            name=full_name,
            customer_id=customer_id,
            age=age,
            address=address,
        )

    def generate_otp(self, length: int = 6) -> str:
        """
        Generate a fake OTP.

        Args:
            length: OTP length (default 6)

        Returns:
            Numeric string OTP
        """
        # Avoid obvious patterns like 000000, 123456
        while True:
            otp = "".join(str(self.rng.randint(0, 9)) for _ in range(length))
            # Reject if all same digit or sequential
            if len(set(otp)) > 1 and otp not in ["123456", "654321"]:
                return otp

    def generate_aadhaar(self) -> str:
        """
        Generate a fake Aadhaar number (12 digits).

        Note: Real Aadhaar uses Verhoeff checksum. This generates
        random 12 digits that look like Aadhaar but won't validate.

        Returns:
            12-digit fake Aadhaar number
        """
        # Aadhaar starts with 2-9 (not 0 or 1)
        first_digit = str(self.rng.randint(2, 9))
        remaining = "".join(str(self.rng.randint(0, 9)) for _ in range(11))
        return first_digit + remaining

    def generate_pan(self) -> str:
        """
        Generate a fake PAN (Permanent Account Number).

        PAN format: AAAAA9999A
        - First 5: Letters (3 random + 4th indicates holder type + 5th is surname initial)
        - Next 4: Digits
        - Last 1: Letter (check character)

        Returns:
            10-character fake PAN
        """
        # First 3 letters (random)
        first_three = "".join(self.rng.choice(string.ascii_uppercase) for _ in range(3))

        # 4th letter: holder type (P=Individual is most common)
        holder_type = "P"

        # 5th letter: surname initial
        surname_initial = self.rng.choice(string.ascii_uppercase)

        # 4 digits
        digits = "".join(str(self.rng.randint(0, 9)) for _ in range(4))

        # Last letter (check character - we use random for fake)
        check_char = self.rng.choice(string.ascii_uppercase)

        return f"{first_three}{holder_type}{surname_initial}{digits}{check_char}"


# Singleton instance
_generator_instance: FakeDataGenerator | None = None


def get_fake_data_generator(seed: int | None = None) -> FakeDataGenerator:
    """Get or create fake data generator instance."""
    global _generator_instance
    if _generator_instance is None or seed is not None:
        _generator_instance = FakeDataGenerator(seed)
    return _generator_instance
