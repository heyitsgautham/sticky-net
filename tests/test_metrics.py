"""The /metrics endpoint and the counters the API records."""

from collections.abc import Callable
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from config.settings import Settings
from src.agents.honeypot_agent import EngagementResult
from src.agents.policy import EngagementMode
from src.detection.detector import DetectionResult
from src.main import app
from src.metrics import REGISTRY, record_fallback, record_verdict


def sample(name: str, **labels: str) -> float:
    """Current value of one series, 0.0 when it has never been recorded."""
    return REGISTRY.get_sample_value(name, labels) or 0.0


def _body(text: str = "pay now", session_id: str = "metrics-test") -> dict[str, Any]:
    return {
        "sessionId": session_id,
        "message": {"sender": "scammer", "text": text, "timestamp": "2026-01-21T10:15:30Z"},
    }


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _scam_agent(reply: str = "which account?") -> tuple[MagicMock, MagicMock]:
    detector = MagicMock()
    detector.analyze = AsyncMock(
        return_value=DetectionResult(is_scam=True, confidence=0.9, scam_type="banking_fraud")
    )
    agent = MagicMock()
    agent.engage = AsyncMock(
        return_value=EngagementResult(
            response=reply,
            duration_seconds=1,
            notes="",
            conversation_id="c",
            turn_number=1,
            engagement_mode=EngagementMode.AGGRESSIVE,
            should_continue=True,
            extracted_intelligence=None,
        )
    )
    agent._generate_notes = MagicMock(return_value="notes")
    return detector, agent


def test_metrics_endpoint_serves_prometheus_text(client: TestClient) -> None:
    client.get("/health")
    response = client.get("/metrics")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert "sticky_net_http_requests_total" in response.text
    assert 'route="/health"' in response.text


def test_metrics_needs_a_key_in_production(
    client: TestClient, use_settings: Callable[..., Settings]
) -> None:
    assert client.get("/metrics").status_code == 401
    assert client.get("/metrics", headers={"x-api-key": "prod-key-for-tests"}).status_code == 200


def test_requests_are_labelled_by_route_template(client: TestClient) -> None:
    before = sample(
        "sticky_net_http_requests_total", method="POST", route="/api/v1/analyze", status="200"
    )
    client.post("/api/v1/analyze", json={"message": {}})
    after = sample(
        "sticky_net_http_requests_total", method="POST", route="/api/v1/analyze", status="200"
    )
    assert after == before + 1


def test_unknown_paths_share_one_label(client: TestClient) -> None:
    before = sample("sticky_net_http_requests_total", method="GET", route="unrouted", status="404")
    client.get("/wp-admin/setup.php")
    client.get("/.env")
    after = sample("sticky_net_http_requests_total", method="GET", route="unrouted", status="404")
    assert after == before + 2
    assert "wp-admin" not in client.get("/metrics").text


def test_auth_failures_are_counted_by_reason(
    client: TestClient, use_settings: Callable[..., Settings]
) -> None:
    missing = sample("sticky_net_auth_failures_total", reason="missing")
    invalid = sample("sticky_net_auth_failures_total", reason="invalid")

    client.post("/api/v1/analyze", json={})
    client.post("/api/v1/analyze", json={}, headers={"x-api-key": "wrong"})

    assert sample("sticky_net_auth_failures_total", reason="missing") == missing + 1
    assert sample("sticky_net_auth_failures_total", reason="invalid") == invalid + 1
    # The 401 also reaches the request counter, since MetricsMiddleware is outermost.
    assert sample("sticky_net_http_requests_total", method="POST", route="unrouted", status="401")


def test_malformed_bodies_count_as_fallbacks(client: TestClient) -> None:
    before = sample("sticky_net_fallback_replies_total", reason="malformed_request")
    response = client.post("/api/v1/analyze", json={"message": "not an object"})
    assert response.status_code == 200
    assert sample("sticky_net_fallback_replies_total", reason="malformed_request") == before + 1


def test_scam_turn_records_verdict_and_callback(client: TestClient) -> None:
    detector, agent = _scam_agent()
    verdicts = sample(
        "sticky_net_scam_verdicts_total",
        endpoint="analyze",
        scam_detected="true",
        scam_type="banking_fraud",
    )
    sent = sample("sticky_net_guvi_callbacks_total", outcome="sent")
    with (
        patch("src.api.routes.get_detector", return_value=detector),
        patch("src.api.routes.get_agent", return_value=agent),
        patch("src.api.routes.send_guvi_callback", new=AsyncMock(return_value=True)),
    ):
        client.post("/api/v1/analyze", json=_body())

    assert (
        sample(
            "sticky_net_scam_verdicts_total",
            endpoint="analyze",
            scam_detected="true",
            scam_type="banking_fraud",
        )
        == verdicts + 1
    )
    assert sample("sticky_net_guvi_callbacks_total", outcome="sent") == sent + 1


def test_failed_callback_is_counted(client: TestClient) -> None:
    detector, agent = _scam_agent()
    errors = sample("sticky_net_guvi_callbacks_total", outcome="error")
    with (
        patch("src.api.routes.get_detector", return_value=detector),
        patch("src.api.routes.get_agent", return_value=agent),
        patch("src.api.routes.send_guvi_callback", new=AsyncMock(side_effect=OSError("down"))),
    ):
        client.post("/api/v1/analyze", json=_body())
    assert sample("sticky_net_guvi_callbacks_total", outcome="error") == errors + 1


def test_agent_timeout_and_empty_reply_count_as_fallbacks(client: TestClient) -> None:
    detector, agent = _scam_agent(reply="")
    empty = sample("sticky_net_fallback_replies_total", reason="empty_reply")
    with (
        patch("src.api.routes.get_detector", return_value=detector),
        patch("src.api.routes.get_agent", return_value=agent),
        patch("src.api.routes.send_guvi_callback", new=AsyncMock(return_value=True)),
    ):
        client.post("/api/v1/analyze", json=_body())
        agent.engage = AsyncMock(side_effect=TimeoutError)
        timeouts = sample("sticky_net_fallback_replies_total", reason="agent_timeout")
        client.post("/api/v1/analyze", json=_body())

    assert sample("sticky_net_fallback_replies_total", reason="empty_reply") == empty + 1
    assert sample("sticky_net_fallback_replies_total", reason="agent_timeout") == timeouts + 1


def test_route_errors_count_as_fallbacks(client: TestClient) -> None:
    before = sample("sticky_net_fallback_replies_total", reason="error")
    with patch("src.api.routes.get_detector", side_effect=RuntimeError("boom")):
        client.post("/api/v1/analyze", json=_body())
        client.post("/api/v1/analyze/detailed", json=_body())
    assert sample("sticky_net_fallback_replies_total", reason="error") == before + 2


def test_unknown_scam_types_fold_into_others() -> None:
    before = sample(
        "sticky_net_scam_verdicts_total", endpoint="t", scam_detected="true", scam_type="others"
    )
    record_verdict("t", True, "crypto_rug_pull")
    record_verdict("t", False, None)
    assert (
        sample(
            "sticky_net_scam_verdicts_total", endpoint="t", scam_detected="true", scam_type="others"
        )
        == before + 1
    )
    assert (
        sample(
            "sticky_net_scam_verdicts_total", endpoint="t", scam_detected="false", scam_type="none"
        )
        >= 1
    )


def test_record_fallback_rejects_unknown_reasons() -> None:
    with pytest.raises(ValueError, match="unknown fallback reason"):
        record_fallback("cosmic_rays")
