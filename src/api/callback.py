"""GUVI Hackathon callback handler for reporting extracted intelligence."""

import httpx
import structlog
from pydantic import BaseModel

from config.settings import get_settings

# Session IDs come from the caller, so they go into fields, never into the message,
# where a newline in one could forge a log line in console output.
logger = structlog.get_logger(__name__)

# How much of an unexpected GUVI response body to keep in the log.
RESPONSE_SNIPPET_CHARS = 200


class CallbackIntelligence(BaseModel):
    """Intelligence payload for GUVI callback."""

    bankAccounts: list[str] = []
    upiIds: list[str] = []
    phishingLinks: list[str] = []
    phoneNumbers: list[str] = []
    emailAddresses: list[str] = []
    suspiciousKeywords: list[str] = []
    caseIds: list[str] = []
    policyNumbers: list[str] = []
    orderNumbers: list[str] = []


class CallbackPayload(BaseModel):
    """Full payload to send to GUVI callback endpoint."""

    sessionId: str
    status: str = "success"
    scamDetected: bool
    scamType: str | None = None
    confidenceLevel: float | None = None
    totalMessagesExchanged: int
    engagementDurationSeconds: int = 0
    extractedIntelligence: CallbackIntelligence
    engagementMetrics: dict[str, int] = {}
    agentNotes: str


async def send_guvi_callback(
    session_id: str,
    scam_detected: bool,
    total_messages: int,
    intelligence: dict[str, list[str]],
    agent_notes: str,
    engagement_duration: int = 0,
    scam_type: str | None = None,
    confidence: float | None = None,
) -> bool:
    """
    Send extracted intelligence to GUVI evaluation endpoint.

    Args:
        session_id: Unique session ID from the platform
        scam_detected: Whether scam intent was confirmed
        total_messages: Total messages exchanged in session
        intelligence: Dict with bankAccounts, upiIds, phishingLinks, phoneNumbers,
            emailAddresses, suspiciousKeywords
        agent_notes: Summary of scammer behavior
        engagement_duration: Duration in seconds since first message in this session
        scam_type: Type of scam detected (e.g., 'phishing', 'vishing')
        confidence: Confidence level of scam detection (0.0-1.0)

    Returns:
        True if callback was successful, False otherwise
    """
    settings = get_settings()

    # Check if callback is disabled
    if not settings.guvi_callback_enabled:
        logger.info("GUVI callback disabled, skipping", session_id=session_id)
        return True

    # Build the payload
    callback_intel = CallbackIntelligence(
        bankAccounts=intelligence.get("bankAccounts", []),
        upiIds=intelligence.get("upiIds", []),
        phishingLinks=intelligence.get("phishingLinks", []),
        phoneNumbers=intelligence.get("phoneNumbers", []),
        emailAddresses=intelligence.get("emailAddresses", []),
        suspiciousKeywords=intelligence.get("suspiciousKeywords", []),
        caseIds=intelligence.get("caseIds", []),
        policyNumbers=intelligence.get("policyNumbers", []),
        orderNumbers=intelligence.get("orderNumbers", []),
    )

    payload = CallbackPayload(
        sessionId=session_id,
        status="success",
        scamDetected=scam_detected,
        scamType=scam_type,
        confidenceLevel=confidence,
        totalMessagesExchanged=total_messages,
        engagementDurationSeconds=engagement_duration,
        extractedIntelligence=callback_intel,
        engagementMetrics={
            "engagementDurationSeconds": engagement_duration,
            "totalMessagesExchanged": total_messages,
        },
        agentNotes=agent_notes,
    )

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                settings.guvi_callback_url,
                json=payload.model_dump(),
                headers={"Content-Type": "application/json"},
                timeout=settings.guvi_callback_timeout,
            )

            if response.status_code in (200, 201, 202):
                logger.info(
                    "GUVI callback successful",
                    session_id=session_id,
                    status_code=response.status_code,
                )
                return True
            else:
                logger.warning(
                    "GUVI callback rejected",
                    session_id=session_id,
                    status_code=response.status_code,
                    body=response.text[:RESPONSE_SNIPPET_CHARS],
                )
                return False

    except httpx.TimeoutException:
        logger.error("GUVI callback timed out", session_id=session_id)
        return False
    except httpx.RequestError as e:
        logger.error("GUVI callback request failed", session_id=session_id, error=str(e))
        return False
    except Exception as e:
        logger.error("Unexpected error in GUVI callback", session_id=session_id, error=str(e))
        return False
