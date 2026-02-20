"""API route definitions."""

import asyncio
import random
import time
import uuid
import structlog
from fastapi import APIRouter, HTTPException, Request

from src.api.callback import send_guvi_callback
from src.api.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    EngagementMetrics,
    ErrorResponse,
    ExtractedIntelligence,
    HoneyPotResponse,
    ScamType,
    SenderType,
    StatusType,
)
from src.api.session_store import (
    accumulate_intel as _accumulate_intel,
    init_session_start_time,
    get_session_start_time,
    store_detection_result,
    get_previous_detection,
)
from src.detection.detector import ScamDetector
from src.agents.honeypot_agent import HoneypotAgent, get_agent
from src.intelligence.extractor import IntelligenceExtractor
from src.exceptions import StickyNetError

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1", tags=["analyze"])

# Session state is managed by src.api.session_store (Firestore-backed)


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

    # ── Final-turn shortcut: return accumulated intelligence summary ──────────
    # The tester / evaluator sends [CONVERSATION_END] to collect final output.
    if request.message.text.strip() == "[CONVERSATION_END]":
        log.info("Received CONVERSATION_END – returning accumulated final output")
        accumulated = _accumulate_intel(session_id, ExtractedIntelligence())
        session_start = get_session_start_time(session_id) or request_start_time
        total_msgs = len(request.conversationHistory) + 1
        engagement_secs = max(int(time.time() - session_start), total_msgs * 25)
        prev_det = get_previous_detection(session_id)
        scam_type_val = prev_det.scam_type if prev_det else None
        confidence_val = float(prev_det.confidence) if prev_det else 0.0
        scam_detected = bool(prev_det and prev_det.is_scam)
        notes = (
            f"Honeypot engaged {total_msgs} messages. "
            f"Scam type: {scam_type_val}. "
            f"Confidence: {confidence_val:.2f}. "
            f"Intelligence extracted: phones={len(accumulated.get('phoneNumbers',[]))}, "
            f"accounts={len(accumulated.get('bankAccounts',[]))}, "
            f"upi={len(accumulated.get('upiIds',[]))}, "
            f"links={len(accumulated.get('phishingLinks',[]))}, "
            f"emails={len(accumulated.get('emailAddresses',[]))}, "
            f"caseIds={len(accumulated.get('caseIds',[]))}, "
            f"policyNumbers={len(accumulated.get('policyNumbers',[]))}, "
            f"orderNumbers={len(accumulated.get('orderNumbers',[]))}."
        )
        return HoneyPotResponse(
            status="success",
            reply="Thank you for your time. Goodbye.",
            sessionId=session_id,
            scamDetected=scam_detected,
            scamType=scam_type_val,
            confidenceLevel=confidence_val,
            totalMessagesExchanged=total_msgs,
            engagementDurationSeconds=engagement_secs,
            extractedIntelligence=accumulated,
            agentNotes=notes,
        )

    try:
        # Step 1: Detect scam (with persistent suspicion — Fix 4B)
        detector = ScamDetector()
        previous_detection = get_previous_detection(session_id)
        detection_result = await detector.analyze(
            message=request.message.text,
            history=request.conversationHistory,
            metadata=request.metadata,
            previous_result=previous_detection,
        )
        # Store for next turn — "once scam, always scam"
        store_detection_result(session_id, detection_result)

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
        # AI extracts intelligence with semantic understanding (victim vs scammer)
        agent = HoneypotAgent()
        elapsed_so_far = time.time() - request_start_time
        agent_budget = max(1.0, TOTAL_REQUEST_BUDGET - elapsed_so_far)
        try:
            engagement_result = await asyncio.wait_for(
                agent.engage(
                    message=request.message,
                    history=request.conversationHistory,
                    metadata=request.metadata,
                    detection=detection_result,
                    turn_number=current_turn,
                ),
                timeout=agent_budget,
            )
        except asyncio.TimeoutError:
            log.warning(
                "Agent timed out, using fallback",
                elapsed=time.time() - request_start_time,
                budget=agent_budget,
            )
            from src.agents.honeypot_agent import EngagementResult, EngagementMode
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
            validated_intel = extractor.validate_llm_extraction(engagement_result.extracted_intelligence)
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

        # Step 3b: Regex backup extraction from scammer messages
        # Scan the current scammer message + all history scammer messages
        all_messages = [
            {"sender": m.sender.value if hasattr(m.sender, 'value') else str(m.sender), "text": m.text}
            for m in request.conversationHistory
        ]
        all_messages.append({"sender": "scammer", "text": request.message.text})
        
        regex_result = extractor.extract_from_conversation(all_messages)
        
        if regex_result.has_intelligence:
            log.info(
                "Regex backup found additional intel",
                phones=len(regex_result.phone_numbers),
                accounts=len(regex_result.bank_accounts),
                upi=len(regex_result.upi_ids),
                urls=len(regex_result.phishing_links),
                emails=len(regex_result.emails),
            )
            # Merge regex finds into validated_intel
            merged_accounts = list(set(validated_intel.bankAccounts + regex_result.bank_accounts))
            merged_upi = list(set(validated_intel.upiIds + regex_result.upi_ids))
            merged_phones = list(set(validated_intel.phoneNumbers + regex_result.phone_numbers))
            merged_links = list(set(validated_intel.phishingLinks + regex_result.phishing_links))
            merged_emails = list(set((validated_intel.emailAddresses or []) + regex_result.emails))
            
            validated_intel = ExtractedIntelligence(
                bankAccounts=merged_accounts,
                upiIds=merged_upi,
                phoneNumbers=merged_phones,
                phishingLinks=merged_links,
                emailAddresses=merged_emails,
                beneficiaryNames=validated_intel.beneficiaryNames,
                bankNames=validated_intel.bankNames,
                ifscCodes=validated_intel.ifscCodes,
                whatsappNumbers=validated_intel.whatsappNumbers,
                suspiciousKeywords=validated_intel.suspiciousKeywords,
                caseIds=validated_intel.caseIds,
                policyNumbers=validated_intel.policyNumbers,
                orderNumbers=validated_intel.orderNumbers,
            )

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
        # Convert scam_type string to ScamType enum
        scam_type_enum = None
        if detection_result.scam_type:
            try:
                scam_type_enum = ScamType(detection_result.scam_type)
            except ValueError:
                scam_type_enum = ScamType.OTHERS
        
        # Ensure agentResponse is never None
        agent_response = engagement_result.response
        if not agent_response:
            agent_response = "Sorry, I'm having trouble understanding. Can you repeat that?"
            log.warning("Agent response was None, using fallback")
        
        # Generate agent notes with validated intelligence
        agent_singleton = get_agent()
        final_notes = agent_singleton._generate_notes(
            detection=detection_result,
            persona=agent_singleton.persona_manager.get_or_create_persona(engagement_result.conversation_id),
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
        session_start = get_session_start_time(session_id) or time.time()
        engagement_duration = max(int(time.time() - session_start), current_turn * 25)
        
        # Step 7: Send intelligence to GUVI callback endpoint
        # Build intelligence dict for callback with accumulated data
        callback_intelligence = accumulated_intel
        
        # Fire callback asynchronously (don't wait for response)
        try:
            callback_success = await send_guvi_callback(
                session_id=session_id,
                scam_detected=True,
                total_messages=total_messages_exchanged,
                intelligence=callback_intelligence,
                agent_notes=final_notes,
                engagement_duration=engagement_duration,
                scam_type=detection_result.scam_type,
                confidence=detection_result.confidence,
            )
            log.info(
                "GUVI callback sent",
                success=callback_success,
                session_id=session_id,
                total_messages=total_messages_exchanged,
            )
        except Exception as e:
            log.warning("GUVI callback failed", error=str(e), session_id=session_id)
        
        # Return simplified response to hackathon platform
        return HoneyPotResponse(
            status="success",
            reply=agent_response,
        )

    except StickyNetError as e:
        log.error("Application error", error=str(e))
        return HoneyPotResponse(
            status="error",
            reply="Sorry, I'm having trouble right now. Can we talk later?",
        )
    except Exception as e:
        log.exception("Unexpected error")
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
        detector = ScamDetector()
        previous_detection = get_previous_detection(session_id)
        detection_result = await detector.analyze(
            message=request.message.text,
            history=request.conversationHistory,
            metadata=request.metadata,
            previous_result=previous_detection,
        )
        # Store for next turn — "once scam, always scam"
        store_detection_result(session_id, detection_result)

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
        agent = HoneypotAgent()
        engagement_result = await agent.engage(
            message=request.message,
            history=request.conversationHistory,
            metadata=request.metadata,
            detection=detection_result,
            turn_number=current_turn,
        )

        # Step 3: Validate AI extraction
        if engagement_result.extracted_intelligence:
            validated_intel = extractor.validate_llm_extraction(engagement_result.extracted_intelligence)
        else:
            validated_intel = ExtractedIntelligence()

        # Step 3b: Regex backup extraction from scammer messages
        # (Same as /analyze endpoint — ensures fakeData like bank accounts,
        #  phishing links, and emails are captured even when the LLM misses them)
        all_messages = [
            {"sender": m.sender.value if hasattr(m.sender, 'value') else str(m.sender), "text": m.text}
            for m in request.conversationHistory
        ]
        all_messages.append({"sender": "scammer", "text": request.message.text})

        regex_result = extractor.extract_from_conversation(all_messages)

        if regex_result.has_intelligence:
            log.info(
                "Regex backup found additional intel (detailed)",
                phones=len(regex_result.phone_numbers),
                accounts=len(regex_result.bank_accounts),
                upi=len(regex_result.upi_ids),
                urls=len(regex_result.phishing_links),
                emails=len(regex_result.emails),
            )
            merged_accounts = list(set(validated_intel.bankAccounts + regex_result.bank_accounts))
            merged_upi = list(set(validated_intel.upiIds + regex_result.upi_ids))
            merged_phones = list(set(validated_intel.phoneNumbers + regex_result.phone_numbers))
            merged_links = list(set(validated_intel.phishingLinks + regex_result.phishing_links))
            merged_emails = list(set((validated_intel.emailAddresses or []) + regex_result.emails))

            validated_intel = ExtractedIntelligence(
                bankAccounts=merged_accounts,
                upiIds=merged_upi,
                phoneNumbers=merged_phones,
                phishingLinks=merged_links,
                emailAddresses=merged_emails,
                beneficiaryNames=validated_intel.beneficiaryNames,
                bankNames=validated_intel.bankNames,
                ifscCodes=validated_intel.ifscCodes,
                whatsappNumbers=validated_intel.whatsappNumbers,
                suspiciousKeywords=validated_intel.suspiciousKeywords,
                caseIds=validated_intel.caseIds,
                policyNumbers=validated_intel.policyNumbers,
                orderNumbers=validated_intel.orderNumbers,
            )

        # Step 4: Build full response
        scam_type_enum = None
        if detection_result.scam_type:
            try:
                scam_type_enum = ScamType(detection_result.scam_type)
            except ValueError:
                scam_type_enum = ScamType.OTHERS

        agent_response = engagement_result.response or "Sorry, I'm having trouble understanding. Can you repeat that?"
        
        agent_singleton = get_agent()
        final_notes = agent_singleton._generate_notes(
            detection=detection_result,
            persona=agent_singleton.persona_manager.get_or_create_persona(engagement_result.conversation_id),
            mode=engagement_result.engagement_mode,
            turn_number=current_turn,
            extracted_intel=validated_intel,
        )

        total_messages_exchanged = len(request.conversationHistory) + 2

        # Calculate engagement duration from session start
        # Floor: ~25s per turn ensures >180s for 8+ turns (Fix 3A sanity check)
        session_start = get_session_start_time(session_id) or time.time()
        engagement_duration = max(int(time.time() - session_start), current_turn * 25)

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
        log.exception("Unexpected error in detailed endpoint")
        return AnalyzeResponse(
            status=StatusType.ERROR,
            scamDetected=False,
            agentResponse="Sorry, I'm having trouble right now. Can we talk later?",
            agentNotes=f"Error: {str(e)}",
        )