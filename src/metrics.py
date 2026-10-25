"""Prometheus metrics for the API, served at ``GET /metrics``.

Everything lives in one private registry, so tests and multiple app instances in
one process never collide with prometheus_client's global default registry.
Label values come from fixed sets or route templates, never from request data,
so a scammer cannot grow the series count by sending odd paths or session IDs.
"""

from prometheus_client import CollectorRegistry, Counter, Histogram, generate_latest
from prometheus_client.exposition import CONTENT_TYPE_LATEST

from src.api.schemas import ScamType

REGISTRY = CollectorRegistry(auto_describe=True)

# Matches the 26 second request budget and the evaluator's 30 second limit.
_LATENCY_BUCKETS = (0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 15.0, 20.0, 26.0, 30.0)

HTTP_REQUESTS = Counter(
    "sticky_net_http_requests_total",
    "HTTP requests by method, route template and status code.",
    ["method", "route", "status"],
    registry=REGISTRY,
)
HTTP_LATENCY = Histogram(
    "sticky_net_http_request_duration_seconds",
    "Time from request to response, by route template.",
    ["route"],
    buckets=_LATENCY_BUCKETS,
    registry=REGISTRY,
)
SCAM_VERDICTS = Counter(
    "sticky_net_scam_verdicts_total",
    "Detector verdicts per analyzed message.",
    ["endpoint", "scam_detected", "scam_type"],
    registry=REGISTRY,
)
AUTH_FAILURES = Counter(
    "sticky_net_auth_failures_total",
    "Requests APIKeyMiddleware rejected, by reason (missing or invalid).",
    ["reason"],
    registry=REGISTRY,
)
FALLBACK_REPLIES = Counter(
    "sticky_net_fallback_replies_total",
    "Turns answered with a canned reply instead of the agent's, by reason.",
    ["reason"],
    registry=REGISTRY,
)
GUVI_CALLBACKS = Counter(
    "sticky_net_guvi_callbacks_total",
    "GUVI evaluator callbacks by outcome (sent, rejected or error).",
    ["outcome"],
    registry=REGISTRY,
)

# Every reason FALLBACK_REPLIES uses, so callers cannot invent new label values.
FALLBACK_REASONS = frozenset({"malformed_request", "agent_timeout", "empty_reply", "error"})

_SCAM_TYPES = frozenset(t.value for t in ScamType)

# Route label for requests no route handled: 404s, and auth rejections that
# APIKeyMiddleware answered before routing. AUTH_FAILURES tells the two apart.
UNROUTED = "unrouted"


def record_fallback(reason: str) -> None:
    """Count one canned reply. ``reason`` must be one of FALLBACK_REASONS."""
    if reason not in FALLBACK_REASONS:
        raise ValueError(f"unknown fallback reason: {reason}")
    FALLBACK_REPLIES.labels(reason=reason).inc()


def record_verdict(endpoint: str, is_scam: bool, scam_type: str | None) -> None:
    """Count one detector verdict. Types outside ScamType count as "others"."""
    if not scam_type:
        label = "none"
    else:
        label = scam_type if scam_type in _SCAM_TYPES else ScamType.OTHERS.value
    SCAM_VERDICTS.labels(
        endpoint=endpoint, scam_detected=str(is_scam).lower(), scam_type=label
    ).inc()


def render_latest() -> tuple[bytes, str]:
    """Return the exposition body and its content type."""
    return generate_latest(REGISTRY), CONTENT_TYPE_LATEST
