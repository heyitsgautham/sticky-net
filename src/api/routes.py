"""API route definitions."""

import random
import structlog
from fastapi import APIRouter, HTTPException, Request

from src.api.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    EngagementMetrics,
    ErrorResponse,
    ExtractedIntelligence,
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
    response_model=AnalyzeResponse,
    responses={
        200: {"model": AnalyzeResponse, "description": "Successful analysis"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        401: {"model": ErrorResponse, "description": "Missing API key"},
        403: {"model": ErrorResponse, "description": "Invalid API key"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def analyze_message(request: AnalyzeRequest) -> AnalyzeResponse:
    """
    Analyze incoming message for scam detection and engagement.

    This endpoint:
    1. Analyzes the message for scam indicators
    2. If scam detected, activates AI agent for engagement
    3. Extracts intelligence from conversation
    4. Returns structured response with metrics
    """
    log = logger.bind(
        channel=request.metadata.channel,
        history_length=len(request.conversationHistory),
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
            
            return AnalyzeResponse(
                status=StatusType.SUCCESS,
                scamDetected=False,
                scamType=None,
                confidence=detection_result.confidence,
                agentNotes="No scam indicators detected",
                agentResponse=random.choice(normal_responses),
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
        
        return AnalyzeResponse(
            status=StatusType.SUCCESS,
            scamDetected=True,
            scamType=scam_type_enum,
            confidence=detection_result.confidence,
            engagementMetrics=EngagementMetrics(
                engagementDurationSeconds=engagement_result.duration_seconds,
                totalMessagesExchanged=current_turn,
            ),
            extractedIntelligence=validated_intel,
            agentNotes=final_notes,
            agentResponse=agent_response,
        )

    except StickyNetError as e:
        log.error("Application error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        log.exception("Unexpected error")
        raise HTTPException(status_code=500, detail="Internal server error")