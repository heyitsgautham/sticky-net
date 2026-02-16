"""GUVI Hackathon callback handler for reporting extracted intelligence."""

import logging
import httpx
from pydantic import BaseModel

from config.settings import get_settings

logger = logging.getLogger(__name__)


class CallbackIntelligence(BaseModel):
    """Intelligence payload for GUVI callback."""
    bankAccounts: list[str] = []
    upiIds: list[str] = []
    phishingLinks: list[str] = []
    phoneNumbers: list[str] = []
    emailAddresses: list[str] = []
    suspiciousKeywords: list[str] = []


class CallbackPayload(BaseModel):
    """Full payload to send to GUVI callback endpoint."""
    sessionId: str
    status: str = "success"
    scamDetected: bool
    totalMessagesExchanged: int
    extractedIntelligence: CallbackIntelligence
    engagementMetrics: dict = {}
    agentNotes: str


async def send_guvi_callback(
    session_id: str,
    scam_detected: bool,
    total_messages: int,
    intelligence: dict,
    agent_notes: str,
    engagement_duration: int = 0,
) -> bool:
    """
    Send extracted intelligence to GUVI evaluation endpoint.
    
    Args:
        session_id: Unique session ID from the platform
        scam_detected: Whether scam intent was confirmed
        total_messages: Total messages exchanged in session
        intelligence: Dict with bankAccounts, upiIds, phishingLinks, phoneNumbers, emailAddresses, suspiciousKeywords
        agent_notes: Summary of scammer behavior
        engagement_duration: Duration in seconds since first message in this session
        
    Returns:
        True if callback was successful, False otherwise
    """
    settings = get_settings()
    
    # Check if callback is disabled
    if not settings.guvi_callback_enabled:
        logger.info(f"GUVI callback disabled, skipping for session {session_id}")
        return True
    
    # Build the payload
    callback_intel = CallbackIntelligence(
        bankAccounts=intelligence.get("bankAccounts", []),
        upiIds=intelligence.get("upiIds", []),
        phishingLinks=intelligence.get("phishingLinks", []),
        phoneNumbers=intelligence.get("phoneNumbers", []),
        emailAddresses=intelligence.get("emailAddresses", []),
        suspiciousKeywords=intelligence.get("suspiciousKeywords", [])
    )
    
    payload = CallbackPayload(
        sessionId=session_id,
        status="success",
        scamDetected=scam_detected,
        totalMessagesExchanged=total_messages,
        extractedIntelligence=callback_intel,
        engagementMetrics={
            "engagementDurationSeconds": engagement_duration,
            "totalMessagesExchanged": total_messages,
        },
        agentNotes=agent_notes
    )
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                settings.guvi_callback_url,
                json=payload.model_dump(),
                headers={"Content-Type": "application/json"},
                timeout=settings.guvi_callback_timeout
            )
            
            if response.status_code in (200, 201, 202):
                logger.info(f"GUVI callback successful for session {session_id}: {response.status_code}")
                return True
            else:
                logger.warning(f"GUVI callback returned {response.status_code} for session {session_id}: {response.text}")
                return False
                
    except httpx.TimeoutException:
        logger.error(f"GUVI callback timed out for session {session_id}")
        return False
    except httpx.RequestError as e:
        logger.error(f"GUVI callback request failed for session {session_id}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error in GUVI callback for session {session_id}: {e}")
        return False


def send_guvi_callback_sync(
    session_id: str,
    scam_detected: bool,
    total_messages: int,
    intelligence: dict,
    agent_notes: str,
    engagement_duration: int = 0,
) -> bool:
    """
    Synchronous version of send_guvi_callback.
    Uses httpx synchronous client.
    """
    settings = get_settings()
    
    # Check if callback is disabled
    if not settings.guvi_callback_enabled:
        logger.info(f"GUVI callback disabled, skipping for session {session_id}")
        return True
    
    callback_intel = CallbackIntelligence(
        bankAccounts=intelligence.get("bankAccounts", []),
        upiIds=intelligence.get("upiIds", []),
        phishingLinks=intelligence.get("phishingLinks", []),
        phoneNumbers=intelligence.get("phoneNumbers", []),
        emailAddresses=intelligence.get("emailAddresses", []),
        suspiciousKeywords=intelligence.get("suspiciousKeywords", [])
    )
    
    payload = CallbackPayload(
        sessionId=session_id,
        status="success",
        scamDetected=scam_detected,
        totalMessagesExchanged=total_messages,
        extractedIntelligence=callback_intel,
        engagementMetrics={
            "engagementDurationSeconds": engagement_duration,
            "totalMessagesExchanged": total_messages,
        },
        agentNotes=agent_notes
    )
    
    try:
        with httpx.Client() as client:
            response = client.post(
                settings.guvi_callback_url,
                json=payload.model_dump(),
                headers={"Content-Type": "application/json"},
                timeout=settings.guvi_callback_timeout
            )
            
            if response.status_code in (200, 201, 202):
                logger.info(f"GUVI callback successful for session {session_id}: {response.status_code}")
                return True
            else:
                logger.warning(f"GUVI callback returned {response.status_code}: {response.text}")
                return False
                
    except Exception as e:
        logger.error(f"GUVI callback failed for session {session_id}: {e}")
        return False
