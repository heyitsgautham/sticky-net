"""Pydantic models for API request/response validation."""

from datetime import datetime
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, Field


class SenderType(str, Enum):
    """Message sender type."""

    SCAMMER = "scammer"
    USER = "user"


class ChannelType(str, Enum):
    """Communication channel type."""

    SMS = "SMS"
    WHATSAPP = "WhatsApp"
    EMAIL = "Email"
    CHAT = "Chat"


class Message(BaseModel):
    """Incoming message model."""

    sender: SenderType
    text: Annotated[str, Field(min_length=1, max_length=5000)]
    timestamp: datetime


class ConversationMessage(BaseModel):
    """Message in conversation history."""

    sender: SenderType
    text: str
    timestamp: datetime


class Metadata(BaseModel):
    """Request metadata."""

    channel: ChannelType = ChannelType.SMS
    language: str = "English"
    locale: str = "IN"


class AnalyzeRequest(BaseModel):
    """Main API request model."""

    message: Message
    conversationHistory: list[ConversationMessage] = Field(default_factory=list)
    metadata: Metadata = Field(default_factory=Metadata)

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


class StatusType(str, Enum):
    """Response status type."""

    SUCCESS = "success"
    ERROR = "error"


class AnalyzeResponse(BaseModel):
    """Main API response model."""

    status: StatusType = StatusType.SUCCESS
    scamDetected: bool
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
                    "engagementMetrics": {
                        "engagementDurationSeconds": 420,
                        "totalMessagesExchanged": 18,
                    },
                    "extractedIntelligence": {
                        "bankAccounts": ["XXXX-XXXX-XXXX"],
                        "upiIds": ["scammer@upi"],
                        "phoneNumbers": ["9876543210"],
                        "phishingLinks": ["http://malicious-link.example"],
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
