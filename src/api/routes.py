"""API route definitions."""

import structlog
from fastapi import APIRouter, HTTPException, Request

from src.api.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    EngagementMetrics,
    ErrorResponse,
    ExtractedIntelligence,
    StatusType,
)
from src.detection.detector import ScamDetector
from src.agents.honeypot_agent import HoneypotAgent
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
            return AnalyzeResponse(
                status=StatusType.SUCCESS,
                scamDetected=False,
                agentNotes="No scam indicators detected",
            )

        log.info("Scam detected", confidence=detection_result.confidence)

        # Step 2: Engage with AI agent
        agent = HoneypotAgent()
        engagement_result = await agent.engage(
            message=request.message,
            history=request.conversationHistory,
            metadata=request.metadata,
            detection=detection_result,
        )

        # Step 3: Extract intelligence
        extractor = IntelligenceExtractor()
        all_messages = [
            *[m.text for m in request.conversationHistory],
            request.message.text,
        ]
        intelligence = await extractor.extract(all_messages)

        # Step 4: Build response
        return AnalyzeResponse(
            status=StatusType.SUCCESS,
            scamDetected=True,
            engagementMetrics=EngagementMetrics(
                engagementDurationSeconds=engagement_result.duration_seconds,
                totalMessagesExchanged=len(request.conversationHistory) + 1,
            ),
            extractedIntelligence=ExtractedIntelligence(
                bankAccounts=intelligence.bank_accounts,
                upiIds=intelligence.upi_ids,
                phishingLinks=intelligence.phishing_links,
            ),
            agentNotes=engagement_result.notes,
            agentResponse=engagement_result.response,
        )

    except StickyNetError as e:
        log.error("Application error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        log.exception("Unexpected error")
        raise HTTPException(status_code=500, detail="Internal server error")