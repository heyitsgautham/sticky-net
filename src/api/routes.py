"""API route definitions."""

import asyncio
import random
import time
import uuid
from collections.abc import Coroutine
from typing import Any

import structlog
from fastapi import APIRouter

from src.agents.honeypot_agent import get_agent
from src.api.callback import send_guvi_callback
from src.api.final_output import (
    CONVERSATION_END,
    conversation_end_response,
    engagement_seconds,
    to_scam_type,
)
from src.api.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    EngagementMetrics,
    ErrorResponse,
    HoneyPotResponse,
    StatusType,
)
from src.api.session_store import (
    accumulate_intel as _accumulate_intel,
)
from src.api.session_store import (
    init_session_start_time,
)
from src.detection.detector import get_detector
from src.error_tracking import capture_exception
from src.exceptions import StickyNetError
from src.metrics import GUVI_CALLBACKS, record_fallback
from src.services.turn_pipeline import TurnPipeline, messages_exchanged

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1", tags=["analyze"])

# Hard cap on one /analyze turn, so the reply reaches the evaluator inside its 30s.
TOTAL_REQUEST_BUDGET = 26.0

# Replies to messages the detector judged harmless.
NON_SCAM_REPLIES = (
    "Hello! How can I help you today?",
    "Hi there! Is everything alright?",
    "Hey! What can I do for you?",
    "Hello! Yes, I'm here. What's up?",
    "Hi! I'm listening. What did you want to tell me?",
)

# agentNotes for a failed /analyze/detailed call. It never includes the exception text.
DETAILED_ERROR_NOTES = "Analysis failed; see server logs for details."

# Session state is managed by src.api.session_store (Firestore-backed)


# The event loop keeps only weak references to tasks, so a fire-and-forget task with
# no other reference can be garbage collected before it finishes. Each callback task
# stays in this set until it completes.
_background_tasks: set[asyncio.Task[None]] = set()


def _run_in_background(coro: Coroutine[Any, Any, None]) -> None:
    """Schedule ``coro`` without awaiting it, holding a reference until it finishes."""
    task = asyncio.create_task(coro)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


async def _fire_callback(**kwargs: Any) -> None:
    """Fire-and-forget GUVI callback. Exceptions are silently logged."""
    try:
        success = await send_guvi_callback(scam_detected=True, **kwargs)
        GUVI_CALLBACKS.labels(outcome="sent" if success else "rejected").inc()
        logger.info("GUVI callback sent", success=success, session_id=kwargs.get("session_id"))
    except Exception as e:
        GUVI_CALLBACKS.labels(outcome="error").inc()
        logger.warning("GUVI callback failed", error=str(e))
        capture_exception(e, component="guvi_callback", session_id=kwargs.get("session_id"))


@router.post(
    "/analyze",
    response_model=HoneyPotResponse,
    responses={
        200: {"model": HoneyPotResponse, "description": "Successful analysis"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        401: {"model": ErrorResponse, "description": "Missing API key"},
        403: {"model": ErrorResponse, "description": "Invalid API key"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def analyze_message(request: AnalyzeRequest) -> HoneyPotResponse:
    """
    Analyze incoming message for scam detection and engagement.

    This endpoint:
    1. Analyzes the message for scam indicators
    2. If scam detected, activates AI agent for engagement
    3. Extracts intelligence from conversation
    4. Returns simplified response with agent reply
    5. Sends full intelligence to GUVI callback endpoint
    """
    # Get or generate session ID
    session_id = request.sessionId or str(uuid.uuid4())

    # Track session start time for engagement duration (Firestore-backed)
    init_session_start_time(session_id)

    log = logger.bind(
        channel=request.metadata.channel,
        history_length=len(request.conversationHistory),
        session_id=session_id,
    )
    log.info("Processing analyze request")
    request_start_time = time.time()  # Track for overall 30s budget

    # The tester / evaluator sends [CONVERSATION_END] to collect the final output.
    if request.message.text.strip() == CONVERSATION_END:
        log.info("Received CONVERSATION_END, returning accumulated final output")
        return conversation_end_response(request, session_id, request_start_time)

    try:
        pipeline = TurnPipeline(get_detector(), get_agent, session_id, "analyze", log)
        detection_result = await pipeline.detect(request)

        if not detection_result.is_scam:
            log.info("Message not detected as scam")
            return HoneyPotResponse(status="success", reply=random.choice(NON_SCAM_REPLIES))

        log.info("Scam detected", confidence=detection_result.confidence)

        # The agent never ends the chat itself; the evaluator decides when it stops,
        # and every extra turn scores. Pass the session's intel so the agent asks for
        # what is still missing.
        turn = await pipeline.engage(
            request,
            detection_result,
            deadline=request_start_time + TOTAL_REQUEST_BUDGET,
            share_session_intel=True,
        )
        log.info(
            "Intelligence status (no early exit)",
            bank_accounts=len(turn.intel.bankAccounts),
            phone_numbers=len(turn.intel.phoneNumbers),
            upi_ids=len(turn.intel.upiIds),
            beneficiary_names=len(turn.intel.beneficiaryNames),
            turn=turn.turn_number,
        )

        accumulated_intel = _accumulate_intel(session_id, turn.intel)
        engagement_duration = engagement_seconds(session_id, turn.turn_number, time.time())

        # Fire-and-forget, so the reply never waits on the evaluator's endpoint.
        _run_in_background(
            _fire_callback(
                session_id=session_id,
                total_messages=messages_exchanged(request),
                intelligence=accumulated_intel,
                agent_notes=turn.notes,
                engagement_duration=engagement_duration,
                scam_type=detection_result.scam_type,
                confidence=detection_result.confidence,
            )
        )

        return HoneyPotResponse(status="success", reply=turn.reply)

    except StickyNetError as e:
        record_fallback("error")
        log.error("Application error", error=str(e))
        capture_exception(e, route="/api/v1/analyze", session_id=session_id)
        return HoneyPotResponse(
            status="error",
            reply="Sorry, I'm having trouble right now. Can we talk later?",
        )
    except Exception as e:
        record_fallback("error")
        log.exception("Unexpected error")
        capture_exception(e, route="/api/v1/analyze", session_id=session_id)
        return HoneyPotResponse(
            status="error",
            reply="Sorry, I'm having trouble right now. Can we talk later?",
        )


@router.post(
    "/analyze/detailed",
    response_model=AnalyzeResponse,
    responses={
        200: {"model": AnalyzeResponse, "description": "Detailed analysis response for frontend"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def analyze_message_detailed(request: AnalyzeRequest) -> AnalyzeResponse:
    """
    Analyze incoming message with full response details.

    This endpoint provides complete analysis data including:
    - Full extracted intelligence
    - Detection metrics
    - Agent notes

    Intended for frontend demo/testing, not for hackathon evaluation.
    """
    session_id = request.sessionId or str(uuid.uuid4())

    # Track session start time for engagement duration
    init_session_start_time(session_id)

    log = logger.bind(
        channel=request.metadata.channel,
        history_length=len(request.conversationHistory),
        session_id=session_id,
    )
    log.info("Processing detailed analyze request")

    try:
        pipeline = TurnPipeline(get_detector(), get_agent, session_id, "analyze_detailed", log)
        detection_result = await pipeline.detect(request)

        if not detection_result.is_scam:
            log.info("Message not detected as scam")
            return AnalyzeResponse(
                status=StatusType.SUCCESS,
                scamDetected=False,
                confidence=detection_result.confidence,
                agentResponse="Hello! How can I help you today?",
            )

        log.info("Scam detected", confidence=detection_result.confidence)
        turn = await pipeline.engage(request, detection_result)

        return AnalyzeResponse(
            status=StatusType.SUCCESS,
            scamDetected=True,
            scamType=to_scam_type(detection_result.scam_type),
            confidence=detection_result.confidence,
            engagementMetrics=EngagementMetrics(
                engagementDurationSeconds=engagement_seconds(
                    session_id, turn.turn_number, time.time()
                ),
                totalMessagesExchanged=messages_exchanged(request),
            ),
            extractedIntelligence=turn.intel,
            agentNotes=turn.notes,
            agentResponse=turn.reply,
        )

    except Exception as e:
        # The traceback goes to the logs and error tracking only; exception text can name paths,
        # credentials or upstream responses, so the client gets a fixed note.
        record_fallback("error")
        log.exception("Unexpected error in detailed endpoint")
        capture_exception(e, route="/api/v1/analyze/detailed", session_id=session_id)
        return AnalyzeResponse(
            status=StatusType.ERROR,
            scamDetected=False,
            agentResponse="Sorry, I'm having trouble right now. Can we talk later?",
            agentNotes=DETAILED_ERROR_NOTES,
        )
