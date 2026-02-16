"""API route definitions."""

import random
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
    OtherIntelItem,
    ScamType,
    SenderType,
    StatusType,
)
from src.detection.detector import ScamDetector
from src.agents.honeypot_agent import HoneypotAgent, get_agent
from src.agents.policy import EngagementPolicy
from src.intelligence.extractor import IntelligenceExtractor
from src.exceptions import StickyNetError

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1", tags=["analyze"])


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
    
    log = logger.bind(
        channel=request.metadata.channel,
        history_length=len(request.conversationHistory),
        session_id=session_id,
    )
    log.info("Processing analyze request")

    try:
        # Step 1: Detect scam
        detector = ScamDetector()
        detection_result = await detector.analyze(
            message=request.message.text,
            history=request.conversationHistory,
            metadata=request.metadata,
        )

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
        
        # Exit responses when high-value intelligence is extracted
        exit_responses = [
            # Original responses
            "okay i am calling that number now, hold on...",
            "wait my son just came home, let me ask him to help me with this",
            "one second, someone is at the door, i will call you back",
            "okay i sent the money, now my phone is dying, i need to charge it",
            "hold on, i am getting another call from my bank, let me check",
            # New variety - domestic interruptions
            "oh no my doorbell is ringing, someone is at the door... i will do this later",
            "sorry my neighbor aunty just came, i have to go help her with something urgent",
            "arey my grandson is crying, i need to check on him... one minute",
            "oh god my cooking is burning on the stove! i smell smoke!! wait wait",
            "wait my daughter-in-law is calling me for lunch, i have to go eat first",
            "oh the milk is boiling over! wait wait i have to go to kitchen!!",
            # New variety - health/personal
            "my blood pressure medicine time ho gaya, i feel dizzy... let me take rest",
            "ji actually i just remembered i have doctor appointment today, need to leave now",
            "sorry sir power cut ho gaya, my phone battery is only 2%... will call you back",
            # New variety - skepticism/confusion
            "wait i am getting another call, it shows BANK on my phone... should i pick up??",
            "hold on my beti is asking who i am talking to, she looks worried...",
            "one second, my husband just came and he is asking what i am doing on phone",
        ]

        # Step 2: Engage with AI agent FIRST (AI-first approach)
        # AI extracts intelligence with semantic understanding (victim vs scammer)
        agent = HoneypotAgent()
        engagement_result = await agent.engage(
            message=request.message,
            history=request.conversationHistory,
            metadata=request.metadata,
            detection=detection_result,
            turn_number=current_turn,
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
                other_info=len(validated_intel.other_critical_info),
            )
        else:
            # No AI extraction - return empty
            validated_intel = ExtractedIntelligence()
            log.warning("No AI extraction available")

        # Step 4: Check exit condition AFTER getting AI extraction
        policy = EngagementPolicy()
        high_value_complete = policy.is_high_value_intelligence_complete(
            bank_accounts=validated_intel.bankAccounts,
            phone_numbers=validated_intel.phoneNumbers,
            upi_ids=validated_intel.upiIds,
            beneficiary_names=validated_intel.beneficiaryNames,
        )
        
        if high_value_complete:
            log.info(
                "High-value intelligence complete, will exit on next turn",
                bank_accounts=len(validated_intel.bankAccounts),
                phone_numbers=len(validated_intel.phoneNumbers),
                upi_ids=len(validated_intel.upiIds),
                beneficiary_names=len(validated_intel.beneficiaryNames),
            )
            # Use exit response for NEXT turn (this turn already has AI response)
            # The frontend will pass this intelligence back, and we'll exit then

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
        
        # Step 6: Send intelligence to GUVI callback endpoint
        # Build intelligence dict for callback
        callback_intelligence = {
            "bankAccounts": validated_intel.bankAccounts,
            "upiIds": validated_intel.upiIds,
            "phishingLinks": validated_intel.phishingLinks,
            "phoneNumbers": validated_intel.phoneNumbers,
            "suspiciousKeywords": validated_intel.suspiciousKeywords,
        }
        
        # Fire callback asynchronously (don't wait for response)
        try:
            callback_success = await send_guvi_callback(
                session_id=session_id,
                scam_detected=True,
                total_messages=total_messages_exchanged,
                intelligence=callback_intelligence,
                agent_notes=final_notes,
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
    
    log = logger.bind(
        channel=request.metadata.channel,
        history_length=len(request.conversationHistory),
        session_id=session_id,
    )
    log.info("Processing detailed analyze request")

    try:
        # Step 1: Detect scam
        detector = ScamDetector()
        detection_result = await detector.analyze(
            message=request.message.text,
            history=request.conversationHistory,
            metadata=request.metadata,
        )

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

        return AnalyzeResponse(
            status=StatusType.SUCCESS,
            scamDetected=True,
            scamType=scam_type_enum,
            confidence=detection_result.confidence,
            engagementMetrics=EngagementMetrics(
                engagementDurationSeconds=0,
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


@router.post(
    "/simple",
    response_model=HoneyPotResponse,
    responses={
        200: {"model": HoneyPotResponse, "description": "Successful analysis"},
    },
)
async def simple_test(request: AnalyzeRequest) -> HoneyPotResponse:
    """
    Simple test endpoint that returns static response immediately.
    
    This endpoint bypasses all LLM calls and returns a pre-defined response
    to test if timeout is the issue with the hackathon validator.
    """
    # Get or generate session ID
    session_id = request.sessionId or str(uuid.uuid4())
    
    logger.info("Simple test endpoint called", sender=request.message.sender, session_id=session_id)
    
    # Calculate totalMessagesExchanged: history + current message + agent reply
    total_messages_exchanged = len(request.conversationHistory) + 2
    
    # Static intelligence for testing
    callback_intelligence = {
        "bankAccounts": ["1234567890123456"],
        "upiIds": ["scammer@paytm"],
        "phishingLinks": ["http://fake-bank-site.com"],
        "phoneNumbers": ["9876543210"],
        "suspiciousKeywords": ["blocked", "urgent", "verify"],
    }
    
    # Send static intelligence to GUVI callback
    try:
        await send_guvi_callback(
            session_id=session_id,
            scam_detected=True,
            total_messages=total_messages_exchanged,
            intelligence=callback_intelligence,
            agent_notes="Static test response - scammer used urgency tactics",
        )
    except Exception as e:
        logger.warning("GUVI callback failed in simple endpoint", error=str(e))
    
    # Return simplified response
    return HoneyPotResponse(
        status="success",
        reply="Oh no! What should I do? Please help me save my account!",
    )