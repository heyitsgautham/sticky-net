"""Pydantic models for API request/response validation."""

from datetime import datetime
from enum import Enum
from typing import Annotated, Union

from pydantic import BaseModel, Field, field_validator


class SenderType(str, Enum):
    """Common sender types (for reference only)."""

    SCAMMER = "scammer"
    USER = "user"


class ChannelType(str, Enum):
    """Common communication channel types (for reference only)."""

    SMS = "SMS"
    WHATSAPP = "WhatsApp"
    EMAIL = "Email"
    CHAT = "Chat"


class Message(BaseModel):
    """Incoming message model."""

    sender: str  # Accept any sender identifier
    text: Annotated[str, Field(min_length=1, max_length=10000)]  # Increased limit for long scam messages
    timestamp: Union[int, str, datetime]  # Accept epoch ms (int), ISO string, or datetime

    @field_validator("timestamp", mode="before")
    @classmethod
    def normalize_timestamp(cls, v: Union[int, str, datetime]) -> datetime:
        """Normalize timestamp to datetime object."""
        if isinstance(v, datetime):
            return v
        if isinstance(v, int):
            # Epoch milliseconds -> convert to datetime
            return datetime.fromtimestamp(v / 1000.0)
        if isinstance(v, str):
            # ISO format string -> parse to datetime
            # Handle both with and without timezone
            try:
                return datetime.fromisoformat(v.replace("Z", "+00:00"))
            except ValueError:
                # Fallback: try parsing without timezone
                return datetime.fromisoformat(v)
        raise ValueError(f"Invalid timestamp format: {v}")


class ConversationMessage(BaseModel):
    """Message in conversation history."""

    sender: str  # Accept any sender identifier
    text: str
    timestamp: Union[int, str, datetime]  # Accept epoch ms (int), ISO string, or datetime

    @field_validator("timestamp", mode="before")
    @classmethod
    def normalize_timestamp(cls, v: Union[int, str, datetime]) -> datetime:
        """Normalize timestamp to datetime object (same logic as Message)."""
        if isinstance(v, datetime):
            return v
        if isinstance(v, (int, float)):
            # Epoch milliseconds -> convert to datetime
            return datetime.fromtimestamp(v / 1000.0)
        if isinstance(v, str):
            # Try epoch string first
            try:
                epoch = float(v)
                return datetime.fromtimestamp(epoch / 1000.0)
            except ValueError:
                pass
            # ISO format string -> parse to datetime
            try:
                return datetime.fromisoformat(v.replace("Z", "+00:00"))
            except ValueError:
                return datetime.fromisoformat(v)
        raise ValueError(f"Invalid timestamp format: {v}")


class Metadata(BaseModel):
    """Request metadata."""

    channel: str = "SMS"  # Accept any string (Telegram, Voice, App, etc.)
    language: str = "English"
    locale: str = "IN"


class AnalyzeRequest(BaseModel):
    """Main API request model."""

    message: Message
    conversationHistory: list[ConversationMessage] = Field(default_factory=list)
    metadata: Metadata = Field(default_factory=Metadata)
    sessionId: str | None = None  # Optional session ID for multi-turn tracking

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "message": {
                        "sender": "scammer",
                        "text": "Your bank account will be blocked today. Verify immediately.",
                        "timestamp": "2026-01-21T10:15:30Z",
                    },
                    "conversationHistory": [],
                    "metadata": {
                        "channel": "SMS",
                        "language": "English",
                        "locale": "IN",
                    },
                }
            ]
        }
    }


class EngagementMetrics(BaseModel):
    """Engagement metrics model."""

    engagementDurationSeconds: int = 0
    totalMessagesExchanged: int = 0


class ExtractedIntelligence(BaseModel):
    """Extracted intelligence model."""

    bankAccounts: list[str] = Field(default_factory=list)
    upiIds: list[str] = Field(default_factory=list)
    phoneNumbers: list[str] = Field(default_factory=list)
    phishingLinks: list[str] = Field(default_factory=list)
    emailAddresses: list[str] = Field(default_factory=list)
    beneficiaryNames: list[str] = Field(default_factory=list)
    bankNames: list[str] = Field(default_factory=list)
    ifscCodes: list[str] = Field(default_factory=list)
    whatsappNumbers: list[str] = Field(default_factory=list)
    suspiciousKeywords: list[str] = Field(default_factory=list)  # Keywords indicating scam
    caseIds: list[str] = Field(default_factory=list)
    policyNumbers: list[str] = Field(default_factory=list)
    orderNumbers: list[str] = Field(default_factory=list)


class AgentJsonResponse(BaseModel):
    """Structured response from the honeypot agent (One-Pass JSON)."""

    reply_text: str  # The message to send back to the scammer
    emotional_tone: str  # The emotion expressed (e.g., "panicked", "confused")
    extracted_intelligence: ExtractedIntelligence  # Intelligence found in this turn
    scam_analysis: dict = Field(default_factory=dict)  # Optional analysis metadata


class StatusType(str, Enum):
    """Response status type."""

    SUCCESS = "success"
    ERROR = "error"


class ScamType(str, Enum):
    """Types of scams that can be detected."""

    JOB_OFFER = "job_offer"
    BANKING_FRAUD = "banking_fraud"
    LOTTERY_REWARD = "lottery_reward"
    IMPERSONATION = "impersonation"
    OTHERS = "others"


class AnalyzeResponse(BaseModel):
    """Main API response model."""

    status: StatusType = StatusType.SUCCESS
    scamDetected: bool
    scamType: ScamType | None = None  # Type of scam detected
    confidence: float = 0.0  # Detection confidence (0.0 to 1.0)
    engagementMetrics: EngagementMetrics = Field(default_factory=EngagementMetrics)
    extractedIntelligence: ExtractedIntelligence = Field(default_factory=ExtractedIntelligence)
    agentNotes: str = ""
    agentResponse: str | None = None  # The response to send back to the scammer

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "status": "success",
                    "scamDetected": True,
                    "scamType": "banking_fraud",
                    "confidence": 0.92,
                    "engagementMetrics": {
                        "engagementDurationSeconds": 420,
                        "totalMessagesExchanged": 18,
                    },
                    "extractedIntelligence": {
                        "bankAccounts": ["XXXX-XXXX-XXXX"],
                        "upiIds": ["scammer@upi"],
                        "phoneNumbers": ["9876543210"],
                        "phishingLinks": ["http://malicious-link.example"],
                        "emailAddresses": ["scammer@example.com"],
                        "beneficiaryNames": ["John Doe"],
                        "bankNames": ["State Bank of India"],
                        "ifscCodes": ["SBIN0001234"],
                        "whatsappNumbers": ["919876543210"],
                    },
                    "agentNotes": "Scammer used urgency tactics and payment redirection",
                    "agentResponse": "Oh no! What do I need to do to verify?",
                }
            ]
        }
    }


class ErrorResponse(BaseModel):
    """Error response model."""

    status: StatusType = StatusType.ERROR
    error: str
    detail: str | None = None


class HoneyPotResponse(BaseModel):
    """Simplified response model for honeypot agent.

    Per-turn: only `status` and `reply` are set.
    Final-turn ([CONVERSATION_END]): all fields are populated so the evaluation
    tooling can score intelligence extraction and scam detection.
    """

    status: str  # "success" or "error"
    reply: str   # The agent's response message

    # Final-output fields (only set when message == '[CONVERSATION_END]')
    sessionId: str | None = None
    scamDetected: bool | None = None
    scamType: str | None = None
    confidenceLevel: float | None = None
    totalMessagesExchanged: int | None = None
    engagementDurationSeconds: int | None = None
    extractedIntelligence: dict | None = None
    agentNotes: str | None = None
