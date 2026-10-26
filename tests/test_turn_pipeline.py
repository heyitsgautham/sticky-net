"""TurnPipeline: the detect, engage and extract steps behind both analyze routes."""

import asyncio
import time
import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.honeypot_agent import EngagementResult
from src.agents.policy import EngagementMode
from src.api.schemas import AnalyzeRequest, ExtractedIntelligence
from src.api.session_store import accumulate_intel, get_previous_detection
from src.detection.detector import DetectionResult
from src.services import turn_pipeline
from src.services.turn_pipeline import (
    EMPTY_REPLY_FALLBACK,
    TIMEOUT_REPLIES,
    TurnPipeline,
    messages_exchanged,
    scammer_turn_number,
)

SCAM = DetectionResult(is_scam=True, confidence=0.9, scam_type="banking_fraud")


def _request(text: str = "pay now", history: list[tuple[str, str]] | None = None) -> AnalyzeRequest:
    return AnalyzeRequest(
        message={"sender": "scammer", "text": text, "timestamp": "2026-01-21T10:15:30Z"},
        conversationHistory=[
            {"sender": sender, "text": t, "timestamp": "2026-01-21T10:14:00Z"}
            for sender, t in (history or [])
        ],
    )


def _engagement(reply: str = "which bank?", intel: ExtractedIntelligence | None = None) -> Any:
    return EngagementResult(
        response=reply,
        duration_seconds=1,
        notes="",
        conversation_id="c-1",
        turn_number=1,
        engagement_mode=EngagementMode.AGGRESSIVE,
        should_continue=True,
        extracted_intelligence=intel,
    )


def _pipeline(
    agent: MagicMock | None = None, detection: DetectionResult = SCAM
) -> tuple[TurnPipeline, MagicMock, MagicMock]:
    detector = MagicMock()
    detector.analyze = AsyncMock(return_value=detection)
    if agent is None:
        agent = MagicMock()
        agent.engage = AsyncMock(return_value=_engagement())
        agent.notes_for = MagicMock(return_value="notes")
    factory = MagicMock(return_value=agent)
    session = f"pipe-{uuid.uuid4()}"
    return TurnPipeline(detector, factory, session, "analyze"), detector, factory


def test_turn_number_counts_only_scammer_messages() -> None:
    request = _request(history=[("scammer", "a"), ("user", "b"), ("scammer", "c")])
    assert scammer_turn_number(request) == 3
    assert messages_exchanged(request) == 5


async def test_detect_passes_the_previous_verdict_and_stores_the_new_one() -> None:
    pipeline, detector, factory = _pipeline()
    first = await pipeline.detect(_request())
    await pipeline.detect(_request())

    assert first is SCAM
    assert detector.analyze.await_args_list[0].kwargs["previous_result"] is None
    assert detector.analyze.await_args_list[1].kwargs["previous_result"] is SCAM
    assert get_previous_detection(pipeline.session_id) is SCAM
    factory.assert_not_called()  # detection alone never builds the agent


async def test_engage_returns_reply_notes_and_turn() -> None:
    pipeline, _, factory = _pipeline()
    turn = await pipeline.engage(_request(history=[("scammer", "hi")]), SCAM)

    assert turn.reply == "which bank?"
    assert turn.notes == "notes"
    assert turn.turn_number == 2
    factory.assert_called_once()


async def test_session_intel_is_shared_only_when_asked() -> None:
    pipeline, _, factory = _pipeline()
    agent = factory.return_value
    accumulate_intel(pipeline.session_id, ExtractedIntelligence(upiIds=["a@okaxis"]))

    await pipeline.engage(_request(), SCAM)
    assert agent.engage.await_args.kwargs["missing_intel"] is None

    await pipeline.engage(_request(), SCAM, share_session_intel=True)
    kwargs = agent.engage.await_args.kwargs
    assert "UPI ID" not in kwargs["missing_intel"]
    assert "bank account number" in kwargs["missing_intel"]
    assert kwargs["extracted_intel"]["upiIds"] == ["a@okaxis"]


async def test_agent_past_the_deadline_gets_a_stalling_reply() -> None:
    async def slow(**_: Any) -> Any:
        await asyncio.sleep(5)
        return _engagement()

    agent = MagicMock()
    agent.engage = slow
    agent.notes_for = MagicMock(return_value="notes")
    pipeline, _, _ = _pipeline(agent)

    with patch.object(turn_pipeline, "MIN_AGENT_SECONDS", 0.01):
        turn = await pipeline.engage(_request(), SCAM, deadline=time.time() - 1)

    assert turn.reply in TIMEOUT_REPLIES
    assert turn.engagement.notes == "Agent timed out; fallback response used"


async def test_empty_agent_reply_is_replaced() -> None:
    agent = MagicMock()
    agent.engage = AsyncMock(return_value=_engagement(reply=""))
    agent.notes_for = MagicMock(return_value="notes")
    pipeline, _, _ = _pipeline(agent)

    turn = await pipeline.engage(_request(), SCAM)
    assert turn.reply == EMPTY_REPLY_FALLBACK


async def test_intel_combines_llm_extraction_and_regex_backup() -> None:
    llm_intel = ExtractedIntelligence(upiIds=["llm.find@okaxis"])
    agent = MagicMock()
    agent.engage = AsyncMock(return_value=_engagement(intel=llm_intel))
    agent.notes_for = MagicMock(return_value="notes")
    pipeline, _, _ = _pipeline(agent)

    request = _request("Call +91-9876543210 now", history=[("scammer", "pay to regex@okaxis")])
    turn = await pipeline.engage(request, SCAM)

    assert set(turn.intel.upiIds) == {"llm.find@okaxis", "regex@okaxis"}
    assert any(p.endswith("9876543210") for p in turn.intel.phoneNumbers)
    notes_intel = agent.notes_for.call_args.args[3]
    assert notes_intel == turn.intel


@pytest.mark.parametrize("intel", [None, ExtractedIntelligence()])
async def test_no_llm_extraction_still_runs_the_regex_pass(
    intel: ExtractedIntelligence | None,
) -> None:
    agent = MagicMock()
    agent.engage = AsyncMock(return_value=_engagement(intel=intel))
    agent.notes_for = MagicMock(return_value="notes")
    pipeline, _, _ = _pipeline(agent)

    turn = await pipeline.engage(_request("send to only.regex@okaxis"), SCAM)
    assert turn.intel.upiIds == ["only.regex@okaxis"]
