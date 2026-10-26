"""API key checks for the ``x-api-key`` header.

Every comparison goes through :func:`hmac.compare_digest`, and every accepted key is
compared, so response time does not reveal how much of a guessed key was right.
"""

import hmac


def key_matches(candidate: str, keys: list[str]) -> bool:
    """True when ``candidate`` equals one of ``keys``, compared in constant time."""
    supplied = candidate.encode()
    matched = False
    for key in keys:
        # No short-circuit, so a match on the first key costs the same as no match.
        matched |= hmac.compare_digest(supplied, key.encode())
    return matched
