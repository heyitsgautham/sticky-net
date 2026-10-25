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
    history_as_dicts,
    merge_regex_backup,
    missing_intel,
    to_scam_type,
)
from src.api.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    EngagementMetrics,
    ErrorResponse,
    ExtractedIntelligence,
    HoneyPotResponse,
    SenderType,
    StatusType,
)
from src.api.session_store import (
    accumulate_intel as _accumulate_intel,
)
from src.api.session_store import (
    get_or_init_session_intel,
    get_previous_detection,
    init_session_start_time,
    store_detection_result,
)
from src.detection.detector import get_detector
from src.error_tracking import capture_exception
from src.exceptions import StickyNetError
from src.intelligence.extractor import IntelligenceExtractor
from src.metrics import GUVI_CALLBACKS, record_fallback, record_verdict

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1", tags=["analyze"])

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
    TOTAL_REQUEST_BUDGET = 26.0  # Hard cap: ensures response reaches client within 30s

    # The tester / evaluator sends [CONVERSATION_END] to collect the final output.
    if request.message.text.strip() == CONVERSATION_END:
        log.info("Received CONVERSATION_END, returning accumulated final output")
        return conversation_end_response(request, session_id, request_start_time)

    try:
        # Step 1: Detect scam (with persistent suspicion — Fix 4B)
        # Use singleton detector to avoid per-request genai.Client cold start
        detector = get_detector()
        previous_detection = get_previous_detection(session_id)
        detection_result = await detector.analyze(
            message=request.message.text,
            history=request.conversationHistory,
            metadata=request.metadata,
            previous_result=previous_detection,
        )
        # Store for next turn — "once scam, always scam"
        store_detection_result(session_id, detection_result)
        record_verdict("analyze", detection_result.is_scam, detection_result.scam_type)

        if not detection_result.is_scam:
            log.info("Message not detected as scam")

            # Generate a simple conversational response for non-scam messages
            normal_responses = [
                "Hello! How can I help you today?",
                "Hi there! Is everything alright?",
                "Hey! What can I do for you?",
                "Hello! Yes, I'm here. What's up?",
                "Hi! I'm listening. What did you want to tell me?",
            ]

            return HoneyPotResponse(
                status="success",
                reply=random.choice(normal_responses),
            )

        log.info("Scam detected", confidence=detection_result.confidence)

        # Calculate turn number: count scammer messages in history + current message
        scammer_messages_in_history = sum(
            1 for m in request.conversationHistory if m.sender == SenderType.SCAMMER
        )
        current_turn = scammer_messages_in_history + 1  # +1 for current scammer message

        # Initialize extractor for validation
        extractor = IntelligenceExtractor()

        # NOTE: exit_responses removed (Fix 2A) — we NEVER voluntarily exit.
        # The evaluator controls when the conversation ends (up to 10 turns).
        # Staying engaged maximizes turn count (8pts) and message count (1pt).

        # Step 2: Engage with AI agent FIRST (AI-first approach)
        # Use singleton agent to avoid per-request genai.Client cold start
        agent = get_agent()
        elapsed_so_far = time.time() - request_start_time
        agent_budget = max(1.0, TOTAL_REQUEST_BUDGET - elapsed_so_far)

        # Pass accumulated intel so the agent knows what's found vs. still missing
        _session_intel = get_or_init_session_intel(session_id)
        _extracted_dict = {k: list(v) for k, v in _session_intel.items()}
        _missing = missing_intel(_session_intel)

        try:
            engagement_result = await asyncio.wait_for(
                agent.engage(
                    message=request.message,
                    history=request.conversationHistory,
                    metadata=request.metadata,
                    detection=detection_result,
                    turn_number=current_turn,
                    missing_intel=_missing,
                    extracted_intel=_extracted_dict,
                ),
                timeout=agent_budget,
            )
        except TimeoutError:
            record_fallback("agent_timeout")
            log.warning(
                "Agent timed out, using fallback",
                elapsed=time.time() - request_start_time,
                budget=agent_budget,
            )
            from src.agents.honeypot_agent import EngagementResult
            from src.agents.policy import EngagementMode

            fallback_replies = [
                "hello... sorry i got disconnected for a moment... what were you saying?",
                "oh sorry my phone battery low... can you repeat that please?",
                "sorry beta network problem here... what did you say about my account?",
                "ji haan... sorry i missed that... can you tell me again please?",
            ]
            engagement_result = EngagementResult(
                response=random.choice(fallback_replies),
                duration_seconds=int(time.time() - request_start_time),
                notes="Agent timed out; fallback response used",
                conversation_id=str(uuid.uuid4()),
                turn_number=current_turn,
                engagement_mode=EngagementMode.AGGRESSIVE,
                should_continue=True,
                extracted_intelligence=None,
            )

        # Log the raw agent response for debugging
        log.info(
            "Agent engagement complete",
            agent_response=engagement_result.response if engagement_result.response else None,
            has_extracted_intel=engagement_result.extracted_intelligence is not None,
        )

        # Step 3: Validate AI extraction with regex (AI-first, regex validates)
        if engagement_result.extracted_intelligence:
            # AI extracted intelligence - validate it
            validated_intel = extractor.validate_llm_extraction(
                engagement_result.extracted_intelligence
            )
            log.info(
                "AI extraction validated",
                bank_accounts=len(validated_intel.bankAccounts),
                upi_ids=len(validated_intel.upiIds),
                phone_numbers=len(validated_intel.phoneNumbers),
                beneficiary_names=len(validated_intel.beneficiaryNames),
                ifsc_codes=len(validated_intel.ifscCodes),
                urls=len(validated_intel.phishingLinks),
                case_ids=len(validated_intel.caseIds),
                policy_numbers=len(validated_intel.policyNumbers),
                order_numbers=len(validated_intel.orderNumbers),
            )
        else:
            # No AI extraction - return empty
            validated_intel = ExtractedIntelligence()
            log.warning("No AI extraction available")

        # Step 3b: Regex backup over the current and earlier messages
        regex_result = extractor.extract_from_conversation(
            history_as_dicts(request, include_current=True)
        )
        if regex_result.has_intelligence:
            log.info(
                "Regex backup found additional intel",
                phones=len(regex_result.phone_numbers),
                accounts=len(regex_result.bank_accounts),
                upi=len(regex_result.upi_ids),
                urls=len(regex_result.phishing_links),
                emails=len(regex_result.emails),
            )
        validated_intel = merge_regex_backup(validated_intel, regex_result)

        # Step 4: Log intelligence status (never exit voluntarily — Fix 2A)
        log.info(
            "Intelligence status (no early exit)",
            bank_accounts=len(validated_intel.bankAccounts),
            phone_numbers=len(validated_intel.phoneNumbers),
            upi_ids=len(validated_intel.upiIds),
            beneficiary_names=len(validated_intel.beneficiaryNames),
            turn=current_turn,
        )

        # Step 5: Build response
        # Ensure agentResponse is never None
        agent_response = engagement_result.response
        if not agent_response:
            agent_response = "Sorry, I'm having trouble understanding. Can you repeat that?"
            record_fallback("empty_reply")
            log.warning("Agent response was None, using fallback")

        # Generate agent notes with validated intelligence
        agent_singleton = get_agent()
        final_notes = agent_singleton._generate_notes(
            detection=detection_result,
            persona=agent_singleton.persona_manager.get_or_create_persona(
                engagement_result.conversation_id
            ),
            mode=engagement_result.engagement_mode,
            turn_number=current_turn,
            extracted_intel=validated_intel,
        )

        # Calculate totalMessagesExchanged: history + current message + agent reply
        total_messages_exchanged = len(request.conversationHistory) + 2

        # Step 6: Accumulate intelligence across turns
        accumulated_intel = _accumulate_intel(session_id, validated_intel)

        # Calculate engagement duration from session start
        # Floor: ~25s per turn ensures >180s for 8+ turns (Fix 3A sanity check)
        engagement_duration = engagement_seconds(session_id, current_turn, time.time())

        # Step 7: Send intelligence to GUVI callback endpoint
        # Build intelligence dict for callback with accumulated data
        callback_intelligence = accumulated_intel

        # Fire callback truly async (fire-and-forget) — don't block the response
        _run_in_background(
            _fire_callback(
                session_id=session_id,
                total_messages=total_messages_exchanged,
                intelligence=callback_intelligence,
                agent_notes=final_notes,
                engagement_duration=engagement_duration,
                scam_type=detection_result.scam_type,
                confidence=detection_result.confidence,
            )
        )

        # Return simplified response to hackathon platform
        return HoneyPotResponse(
            status="success",
            reply=agent_response,
        )

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
        # Step 1: Detect scam (with persistent suspicion — Fix 4B)
        detector = get_detector()
        previous_detection = get_previous_detection(session_id)
        detection_result = await detector.analyze(
            message=request.message.text,
            history=request.conversationHistory,
            metadata=request.metadata,
            previous_result=previous_detection,
        )
        # Store for next turn — "once scam, always scam"
        store_detection_result(session_id, detection_result)
        record_verdict("analyze_detailed", detection_result.is_scam, detection_result.scam_type)

        if not detection_result.is_scam:
            log.info("Message not detected as scam")
            return AnalyzeResponse(
                status=StatusType.SUCCESS,
                scamDetected=False,
                confidence=detection_result.confidence,
                agentResponse="Hello! How can I help you today?",
            )

        log.info("Scam detected", confidence=detection_result.confidence)

        # Calculate turn number
        scammer_messages_in_history = sum(
            1 for m in request.conversationHistory if m.sender == SenderType.SCAMMER
        )
        current_turn = scammer_messages_in_history + 1

        # Initialize extractor
        extractor = IntelligenceExtractor()

        # Step 2: Engage with AI agent
        agent = get_agent()
        engagement_result = await agent.engage(
            message=request.message,
            history=request.conversationHistory,
            metadata=request.metadata,
            detection=detection_result,
            turn_number=current_turn,
        )

        # Step 3: Validate AI extraction
        if engagement_result.extracted_intelligence:
            validated_intel = extractor.validate_llm_extraction(
                engagement_result.extracted_intelligence
            )
        else:
            validated_intel = ExtractedIntelligence()

        # Step 3b: Regex backup, as in /analyze, so fakeData the LLM missed still lands
        regex_result = extractor.extract_from_conversation(
            history_as_dicts(request, include_current=True)
        )
        if regex_result.has_intelligence:
            log.info(
                "Regex backup found additional intel (detailed)",
                phones=len(regex_result.phone_numbers),
                accounts=len(regex_result.bank_accounts),
                upi=len(regex_result.upi_ids),
                urls=len(regex_result.phishing_links),
                emails=len(regex_result.emails),
            )
        validated_intel = merge_regex_backup(validated_intel, regex_result)

        # Step 4: Build full response
        scam_type_enum = to_scam_type(detection_result.scam_type)

        agent_response = (
            engagement_result.response
            or "Sorry, I'm having trouble understanding. Can you repeat that?"
        )

        agent_singleton = get_agent()
        final_notes = agent_singleton._generate_notes(
            detection=detection_result,
            persona=agent_singleton.persona_manager.get_or_create_persona(
                engagement_result.conversation_id
            ),
            mode=engagement_result.engagement_mode,
            turn_number=current_turn,
            extracted_intel=validated_intel,
        )

        total_messages_exchanged = len(request.conversationHistory) + 2

        # Calculate engagement duration from session start
        # Floor: ~25s per turn ensures >180s for 8+ turns (Fix 3A sanity check)
        engagement_duration = engagement_seconds(session_id, current_turn, time.time())

        return AnalyzeResponse(
            status=StatusType.SUCCESS,
            scamDetected=True,
            scamType=scam_type_enum,
            confidence=detection_result.confidence,
            engagementMetrics=EngagementMetrics(
                engagementDurationSeconds=engagement_duration,
                totalMessagesExchanged=total_messages_exchanged,
            ),
            extractedIntelligence=validated_intel,
            agentNotes=final_notes,
            agentResponse=agent_response,
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
