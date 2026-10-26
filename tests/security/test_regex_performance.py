"""Hostile input must not make the regex extraction slow.

Each analyze turn runs the regex extraction over every scammer message in the
history, synchronously on the event loop. A pattern that backtracks quadratically
lets one request of 101 x 10,000 characters stall every other request.
"""

import re
import time

import pytest

from src.api.schemas import MAX_HISTORY_MESSAGES, MAX_MESSAGE_CHARS
from src.intelligence.extractor import IntelligenceExtractor

# The quadratic version took about 14 s on a laptop for this history; linear is ~50 ms.
BUDGET_SECONDS = 1.5

# The handle pattern before the fix, kept to check the fix finds the same matches.
OLD_HANDLE_PATTERN = re.compile(r"([\w.+-]+@[\w.-]+)")


@pytest.mark.parametrize("filler", ["+", "a", ".", "-", "a.b+"])
def test_full_hostile_history_extracts_quickly(filler: str) -> None:
    text = (filler * MAX_MESSAGE_CHARS)[:MAX_MESSAGE_CHARS]
    messages = [{"sender": "scammer", "text": text}] * (MAX_HISTORY_MESSAGES + 1)

    start = time.perf_counter()
    result = IntelligenceExtractor().extract_from_conversation(messages)
    elapsed = time.perf_counter() - start

    assert elapsed < BUDGET_SECONDS, f"{elapsed:.2f}s for filler {filler!r}"
    assert result.upi_ids == []
    assert result.emails == []


@pytest.mark.parametrize(
    "text",
    [
        "pay to fraud.help@okaxis now",
        "mail offers@fake-amazon.co.in or scam@fake.com",
        "a+b@ybl, c.d-e@paytm. x@okaxis.",
        "ids: first@ybl second@okaxis",
        "no handle here",
        "@ybl and user@ and @@ and a@@b",
        "+++user@ybl",
        "prefix!user@ybl",
    ],
)
def test_handle_matches_are_unchanged(text: str) -> None:
    from src.intelligence.extractor import _HANDLE_AT_DOMAIN

    old = [m.group(1) for m in OLD_HANDLE_PATTERN.finditer(text)]
    new = [m.group(1) for m in _HANDLE_AT_DOMAIN.finditer(text)]
    assert new == old


def test_upi_and_email_extraction_still_work() -> None:
    result = IntelligenceExtractor().extract(
        "Send to fraud.help@okaxis or mail refunds@fake-bank.co.in today"
    )
    assert result.upi_ids == ["fraud.help@okaxis"]
    assert result.emails == ["refunds@fake-bank.co.in"]
