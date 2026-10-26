"""Per-client request limits for the API.

A sliding-window log: each client keeps the timestamps of its requests in the last
RATE_LIMIT_WINDOW_SECONDS, and a request that would make more than
RATE_LIMIT_REQUESTS of them is refused. Clients live in a BoundedCache, so a flood of
new client keys evicts idle ones instead of growing memory without bound.
"""

import hashlib
import math
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass

from src.api.bounded_cache import BoundedCache

# Distinct clients tracked at once; the least recently seen is dropped past this.
MAX_TRACKED_CLIENTS = 10_000


@dataclass(frozen=True)
class RateDecision:
    """Outcome of one request against its client's limit."""

    allowed: bool
    limit: int
    remaining: int
    # Whole seconds until the oldest request leaves the window; 0 when allowed.
    retry_after: int


class SlidingWindowLimiter:
    """Counts requests per client key over a sliding time window."""

    def __init__(
        self,
        max_clients: int = MAX_TRACKED_CLIENTS,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._clients: BoundedCache[deque[float]] = BoundedCache(max_clients)
        self._clock = clock

    def hit(self, key: str, limit: int, window_seconds: float) -> RateDecision:
        """Record a request for ``key`` unless it would exceed ``limit`` per window."""
        now = self._clock()
        timestamps = self._clients.get(key)
        if timestamps is None:
            timestamps = deque()
            self._clients[key] = timestamps
        while timestamps and timestamps[0] <= now - window_seconds:
            timestamps.popleft()

        if len(timestamps) >= limit:
            wait = timestamps[0] + window_seconds - now
            return RateDecision(False, limit, 0, max(1, math.ceil(wait)))

        timestamps.append(now)
        return RateDecision(True, limit, limit - len(timestamps), 0)

    def clear(self) -> None:
        """Forget every client, as a restart would."""
        self._clients.clear()


def client_key(api_key: str | None, client_host: str | None, key_is_valid: bool) -> str:
    """Bucket for a request: its API key when valid, otherwise its client address.

    Invalid keys fall back to the address, so cycling made-up keys cannot buy a
    fresh allowance. Keys are hashed, so the limiter never holds one in clear.
    """
    if api_key and key_is_valid:
        return "key:" + hashlib.sha256(api_key.encode()).hexdigest()[:32]
    return f"ip:{client_host or 'unknown'}"


limiter = SlidingWindowLimiter()
