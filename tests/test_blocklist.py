#!/usr/bin/env python3
"""Quick test for beneficiary name blocklist."""

from src.intelligence.validators import validate_beneficiary_name, BENEFICIARY_NAME_BLOCKLIST

# Test false positives that should be rejected
false_positives = ['Now', 'Before Paying', 'Name', 'Pay Now', 'Send Money', 'Bank Transfer', 'Dear Customer']
print('Testing false positives (should all be False):')
for name in false_positives:
    result = validate_beneficiary_name(name)
    status = "✗ WRONG" if result else "✓ OK"
    print(f'  {status} - {name!r}: {result}')

# Test valid names that should pass
valid_names = ['Rahul Kumar', 'Priya Singh', 'Amit Sharma', 'Sanjay Patel', 'Ravi Verma']
print('\nTesting valid names (should all be True):')
for name in valid_names:
    result = validate_beneficiary_name(name)
    status = "✓ OK" if result else "✗ WRONG"
    print(f'  {status} - {name!r}: {result}')

print(f'\nBlocklist size: {len(BENEFICIARY_NAME_BLOCKLIST)} words')
