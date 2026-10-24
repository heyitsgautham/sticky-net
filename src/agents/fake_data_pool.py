"""Word lists and number prefixes FakeDataGenerator draws from.

The card BINs are test or unissued prefixes, so the numbers pass a Luhn check
but fail at any real processor.
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
    "Kamala",
    "Lakshmi",
    "Saraswati",
    "Parvati",
    "Sita",
    "Radha",
    "Durga",
    "Ganga",
    "Savitri",
    "Shakuntala",
    "Meena",
    "Saroj",
    "Sumitra",
    "Pushpa",
    "Shanti",
    "Kausalya",
    "Urmila",
    "Sunita",
    "Annapurna",
    "Vimala",
]

MALE_FIRST_NAMES = [
    "Ramesh",
    "Suresh",
    "Rajesh",
    "Mahesh",
    "Ganesh",
    "Prakash",
    "Satish",
    "Girish",
    "Harish",
    "Dinesh",
    "Mohan",
    "Sohan",
    "Rohan",
    "Kishan",
    "Shyam",
    "Gopal",
    "Balram",
    "Raghunath",
    "Jagdish",
    "Devendra",
]

LAST_NAMES = [
    "Sharma",
    "Verma",
    "Gupta",
    "Singh",
    "Kumar",
    "Patel",
    "Devi",
    "Rao",
    "Reddy",
    "Nair",
    "Pillai",
    "Menon",
    "Iyer",
    "Iyengar",
    "Agarwal",
    "Joshi",
    "Pandey",
    "Mishra",
    "Dubey",
    "Tiwari",
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
    "Gandhi Nagar",
    "Nehru Colony",
    "Rajiv Chowk",
    "MG Road",
    "Civil Lines",
    "Sadar Bazaar",
    "Station Road",
    "Bank Colony",
    "Teachers Colony",
    "Government Quarters",
    "Old City",
    "Cantonment Area",
    "University Road",
    "Temple Street",
]
