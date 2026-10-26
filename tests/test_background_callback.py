"""The GUVI callback runs as a background task that the event loop cannot lose."""

import asyncio
import uuid
from collections.abc import Iterator
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

import src.api.routes as routes
from src.agents.honeypot_agent import EngagementResult
from src.agents.policy import EngagementMode
from src.detection.detector import DetectionResult
from src.main import app


@pytest.fixture
def scam_turn() -> Iterator[None]:
    detector = MagicMock()
    detector.analyze = AsyncMock(
        return_value=DetectionResult(is_scam=True, confidence=0.9, scam_type="banking_fraud")
    )
    agent = MagicMock()
    agent.engage = AsyncMock(
        return_value=EngagementResult(
            response="which account?",
            duration_seconds=1,
            notes="",
            conversation_id="c",
            turn_number=1,
            engagement_mode=EngagementMode.AGGRESSIVE,
            should_continue=True,
            extracted_intelligence=None,
        )
    )
    agent.notes_for = MagicMock(return_value="notes")
    with (
        patch("src.api.routes.get_detector", return_value=detector),
        patch("src.api.routes.get_agent", return_value=agent),
    ):
        yield


async def test_pending_callback_is_held_until_it_finishes(scam_turn: None) -> None:
    release = asyncio.Event()

    async def slow_callback(**_: object) -> bool:
        await release.wait()
        return True

    body = {
        "sessionId": f"bg-{uuid.uuid4()}",
        "message": {"sender": "scammer", "text": "pay now", "timestamp": "2026-01-21T10:15:30Z"},
    }
    transport = httpx.ASGITransport(app=app)
    with patch("src.api.routes.send_guvi_callback", side_effect=slow_callback):
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/v1/analyze", json=body)
            assert response.json()["reply"] == "which account?"

            # The reply went out while the callback still waits, and the route keeps a
            # strong reference so garbage collection cannot cancel it mid-flight.
            pending = set(routes._background_tasks)
            assert len(pending) == 1
            assert not next(iter(pending)).done()

            release.set()
            await asyncio.gather(*pending)

    assert routes._background_tasks == set()
