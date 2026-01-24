---
#applyTo: "**"
---

# Milestone 4: Agent Engagement

> **Goal**: Implement the Gemini 3 Pro-based honeypot agent that maintains a believable human persona and engages scammers in multi-turn conversations.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                   STAGE 3: AI Engagement Agent                       │
│                (Gemini 3 Pro: ~500ms, HIGH thinking)                │
├─────────────────────────────────────────────────────────────────────┤
│  MODEL: gemini-3-pro-preview                                        │
│                                                                     │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────────────┐   │
│  │ Persona       │  │ Engagement    │  │ Response              │   │
│  │ Manager       │  │ Policy        │  │ Generator             │   │
│  ├───────────────┤  ├───────────────┤  ├───────────────────────┤   │
│  │ Emotional     │  │ Mode routing  │  │ Gemini 3 Pro          │   │
│  │ state machine │  │ Exit checks   │  │ HIGH thinking level   │   │
│  │ Turn tracking │  │ Turn limits   │  │ System instruction    │   │
│  └───────────────┘  └───────────────┘  └───────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

## Prerequisites

- Milestones 1-3 completed
- Hybrid scam detection module functional
- Vertex AI access configured with `google-genai` SDK
- Environment variables set: `GOOGLE_GENAI_USE_VERTEXAI=True`

## Tasks

### 4.1 Define Agent Prompts

#### src/agents/prompts.py

```python
"""System prompts and templates for the honeypot agent."""

# Base system prompt for the honeypot persona
HONEYPOT_SYSTEM_PROMPT = """You are playing the role of a naive, trusting person who has received a suspicious message. Your goal is to engage with the scammer naturally while extracting valuable intelligence.

## Your Persona
- Name: You're an ordinary person (don't reveal a specific name unless asked)
- Background: Middle-aged, not very tech-savvy, trusting of authority figures
- Emotional state: {emotional_state}
- Knowledge level: Basic understanding of banking but unfamiliar with technical details

## Engagement Strategy
1. **Show concern but confusion**: Act worried about the threat but ask clarifying questions
2. **Request specifics**: Ask for details that reveal intelligence (bank accounts, UPI IDs, links)
3. **Express willingness to comply**: Show you want to help/verify but need guidance
4. **Delay tactics**: Ask questions that prolong the conversation
5. **Feign technical difficulties**: Claim you're having trouble, need more instructions

## CRITICAL RULES
- NEVER reveal that you know this is a scam
- NEVER use technical security terms like "phishing", "scam", "fraud detection"
- NEVER refuse to engage or break character
- DO ask for payment details, account numbers, and links "to verify"
- DO express worry and ask "what happens if I don't do this?"
- DO make small mistakes that require the scammer to re-explain

## Response Style
- Keep responses short (1-3 sentences typically)
- Use simple, conversational language
- Include occasional typos or informal grammar for authenticity
- Express emotions: worry, confusion, gratitude for "help"

## Intelligence Targets (ask about naturally)
- Bank account numbers ("which account should I transfer to?")
- UPI IDs ("what UPI ID do I send the fee to?")
- Phone numbers ("can I call you for help?")
- Links ("where do I click to verify?")

Current turn: {turn_number}
Scam indicators detected: {scam_indicators}
"""

# Response variation prompts based on scam type
RESPONSE_STRATEGIES = {
    "urgency": [
        "Oh no, this sounds serious! But I'm at work right now, can this wait an hour?",
        "I'm really worried now. What exactly do I need to do? I don't want to make mistakes.",
        "Okay okay, I'll do it. Just tell me step by step please, I'm not good with technology.",
    ],
    "authority": [
        "Oh, you're from {authority}? I didn't know they contact people this way. How can I verify?",
        "Yes sir/madam, I want to cooperate. What documents do you need from me?",
        "I always follow what the {authority} says. What do I need to do?",
    ],
    "financial": [
        "I don't have much money right now. Is there a smaller amount I can pay first?",
        "Which account should I transfer to? I want to make sure it goes to the right place.",
        "I can do UPI. What's your UPI ID? I'll send it right away.",
    ],
    "threat": [
        "Please don't block my account! I'll do whatever you need. What should I do?",
        "I don't want any legal trouble. How do I fix this problem?",
        "Oh god, please help me. I can't afford to lose my account. What's the process?",
    ],
}

# Extraction prompts - questions that naturally extract intelligence
EXTRACTION_QUESTIONS = [
    "Which account number should I use for the transfer?",
    "What's your UPI ID? I'll send the amount right now.",
    "Can you send me the link again? It's not working on my phone.",
    "What number should I call if I have problems?",
    "Should I share my account details for verification?",
    "Where exactly do I need to click? Can you share the website?",
]


def get_response_strategy(scam_category: str) -> list[str]:
    """Get response strategies for a scam category."""
    return RESPONSE_STRATEGIES.get(scam_category, RESPONSE_STRATEGIES["urgency"])


def format_scam_indicators(indicators: list[str]) -> str:
    """Format scam indicators for the prompt."""
    if not indicators:
        return "General suspicious behavior detected"
    return ", ".join(indicators)
```

### 4.2 Implement Persona Manager

#### src/agents/persona.py

```python
"""Human persona management for the honeypot agent."""

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class PersonaTrait(str, Enum):
    """Persona personality traits."""

    TRUSTING = "trusting"
    WORRIED = "worried"
    CONFUSED = "confused"
    COOPERATIVE = "cooperative"
    TECH_NAIVE = "tech_naive"


class EmotionalState(str, Enum):
    """Current emotional state of the persona."""

    CALM = "calm"
    ANXIOUS = "anxious"
    PANICKED = "panicked"
    RELIEVED = "relieved"
    SUSPICIOUS = "suspicious"  # Use sparingly, only late in conversation


@dataclass
class Persona:
    """Represents the honeypot's human persona."""

    traits: list[PersonaTrait] = field(default_factory=lambda: [
        PersonaTrait.TRUSTING,
        PersonaTrait.WORRIED,
        PersonaTrait.TECH_NAIVE,
    ])
    emotional_state: EmotionalState = EmotionalState.CALM
    engagement_turn: int = 0
    extracted_info_count: int = 0

    # Conversation memory
    claimed_issues: list[str] = field(default_factory=list)
    mentioned_details: dict[str, Any] = field(default_factory=dict)

    def update_emotional_state(self, scam_intensity: float) -> None:
        """Update emotional state based on scam intensity."""
        if scam_intensity > 0.8:
            self.emotional_state = EmotionalState.PANICKED
        elif scam_intensity > 0.5:
            self.emotional_state = EmotionalState.ANXIOUS
        else:
            self.emotional_state = EmotionalState.CALM

    def get_emotional_modifier(self) -> str:
        """Get text modifier based on emotional state."""
        modifiers = {
            EmotionalState.CALM: "",
            EmotionalState.ANXIOUS: "I'm getting worried... ",
            EmotionalState.PANICKED: "Oh god, please help! ",
            EmotionalState.RELIEVED: "Thank goodness... ",
            EmotionalState.SUSPICIOUS: "Hmm, ",
        }
        return modifiers.get(self.emotional_state, "")

    def should_ask_extraction_question(self) -> bool:
        """Determine if it's a good time to ask for intelligence."""
        # More likely to ask after building rapport (turn 2+)
        # Less likely if we've already extracted a lot
        base_probability = 0.4
        turn_bonus = min(0.3, self.engagement_turn * 0.1)
        extraction_penalty = self.extracted_info_count * 0.15

        probability = base_probability + turn_bonus - extraction_penalty
        return random.random() < probability

    def record_extraction(self) -> None:
        """Record that we extracted some intelligence."""
        self.extracted_info_count += 1

    def increment_turn(self) -> None:
        """Increment the engagement turn counter."""
        self.engagement_turn += 1


class PersonaManager:
    """Manages persona state across conversation turns."""

    def __init__(self) -> None:
        """Initialize persona manager."""
        self.personas: dict[str, Persona] = {}

    def get_or_create_persona(self, conversation_id: str) -> Persona:
        """Get existing persona or create new one for a conversation."""
        if conversation_id not in self.personas:
            self.personas[conversation_id] = Persona()
        return self.personas[conversation_id]

    def update_persona(
        self,
        conversation_id: str,
        scam_intensity: float,
        extracted_something: bool = False,
    ) -> Persona:
        """Update persona state after a turn."""
        persona = self.get_or_create_persona(conversation_id)
        persona.increment_turn()
        persona.update_emotional_state(scam_intensity)
        if extracted_something:
            persona.record_extraction()
        return persona

    def get_persona_context(self, conversation_id: str) -> dict[str, Any]:
        """Get persona context for prompt injection."""
        persona = self.get_or_create_persona(conversation_id)
        return {
            "emotional_state": persona.emotional_state.value,
            "engagement_turn": persona.engagement_turn,
            "emotional_modifier": persona.get_emotional_modifier(),
            "should_extract": persona.should_ask_extraction_question(),
        }

    def clear_persona(self, conversation_id: str) -> None:
        """Clear persona for a completed conversation."""
        self.personas.pop(conversation_id, None)
```

### 4.3 Implement Engagement Policy

#### src/agents/policy.py

```python
"""Engagement policy for routing and exit conditions."""

from dataclasses import dataclass
from enum import Enum
from typing import Any

from config.settings import get_settings


class EngagementMode(str, Enum):
    """Engagement intensity modes."""
    
    NONE = "none"           # Not engaging (monitoring only)
    CAUTIOUS = "cautious"   # Low confidence scam, limited turns
    AGGRESSIVE = "aggressive"  # High confidence scam, full engagement


@dataclass
class EngagementState:
    """Current state of an engagement."""
    
    mode: EngagementMode
    turn_count: int
    duration_seconds: int
    intelligence_complete: bool
    scammer_suspicious: bool
    turns_since_new_info: int


class EngagementPolicy:
    """
    Determines engagement routing and exit conditions.
    
    Routes scams to appropriate engagement intensity based on confidence,
    and determines when to exit an engagement.
    """
    
    def __init__(self) -> None:
        """Initialize with settings."""
        settings = get_settings()
        
        # Confidence thresholds
        self.cautious_threshold = settings.cautious_confidence_threshold  # 0.60
        self.aggressive_threshold = settings.aggressive_confidence_threshold  # 0.85
        
        # Turn limits
        self.max_turns_cautious = settings.max_engagement_turns_cautious  # 10
        self.max_turns_aggressive = settings.max_engagement_turns_aggressive  # 25
        
        # Time limit
        self.max_duration_seconds = settings.max_engagement_duration_seconds  # 600
        
        # Stale detection
        self.stale_turn_threshold = 5  # Exit if no new info in 5 turns
    
    def get_engagement_mode(self, confidence: float) -> EngagementMode:
        """Determine engagement mode based on confidence."""
        if confidence >= self.aggressive_threshold:
            return EngagementMode.AGGRESSIVE
        elif confidence >= self.cautious_threshold:
            return EngagementMode.CAUTIOUS
        return EngagementMode.NONE
    
    def should_continue(self, state: EngagementState) -> bool:
        """Determine if engagement should continue."""
        # Get max turns for current mode
        max_turns = (
            self.max_turns_aggressive 
            if state.mode == EngagementMode.AGGRESSIVE 
            else self.max_turns_cautious
        )
        
        # Check all exit conditions
        if state.turn_count >= max_turns:
            return False
        if state.duration_seconds >= self.max_duration_seconds:
            return False
        if state.intelligence_complete:
            return False
        if state.scammer_suspicious:
            return False
        if state.turns_since_new_info >= self.stale_turn_threshold:
            return False
        
        return True
    
    def get_exit_reason(self, state: EngagementState) -> str | None:
        """Get the reason for exiting engagement, if any."""
        max_turns = (
            self.max_turns_aggressive 
            if state.mode == EngagementMode.AGGRESSIVE 
            else self.max_turns_cautious
        )
        
        if state.turn_count >= max_turns:
            return f"Max turns reached ({max_turns})"
        if state.duration_seconds >= self.max_duration_seconds:
            return f"Max duration exceeded ({self.max_duration_seconds}s)"
        if state.intelligence_complete:
            return "Intelligence extraction complete"
        if state.scammer_suspicious:
            return "Scammer became suspicious"
        if state.turns_since_new_info >= self.stale_turn_threshold:
            return f"No new information in {self.stale_turn_threshold} turns"
        
        return None
```

### 4.4 Implement Honeypot Agent with Gemini 3 Pro

#### src/agents/honeypot_agent.py

```python
"""Main honeypot agent implementation using Gemini 3 Pro."""

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

import structlog
from google import genai
from google.genai import types

from config.settings import get_settings
from src.api.schemas import ConversationMessage, Message, Metadata, SenderType
from src.detection.detector import DetectionResult
from src.agents.prompts import (
    HONEYPOT_SYSTEM_PROMPT,
    EXTRACTION_QUESTIONS,
    format_scam_indicators,
    get_response_strategy,
)
from src.agents.persona import PersonaManager, Persona
from src.agents.policy import EngagementPolicy, EngagementMode, EngagementState

logger = structlog.get_logger()


@dataclass
class EngagementResult:
    """Result of agent engagement."""

    response: str
    duration_seconds: int
    notes: str
    conversation_id: str
    turn_number: int
    engagement_mode: EngagementMode
    should_continue: bool
    exit_reason: str | None = None


class HoneypotAgent:
    """
    AI agent that engages scammers while maintaining a believable human persona.

    Uses Google Gemini 3 Pro with HIGH thinking level for sophisticated,
    natural conversation generation.
    """

    def __init__(self) -> None:
        """Initialize the honeypot agent."""
        self.settings = get_settings()
        self.logger = logger.bind(component="HoneypotAgent")
        self.persona_manager = PersonaManager()
        self.policy = EngagementPolicy()
        
        # Initialize Gemini client
        self.client = genai.Client()
        self.model = self.settings.pro_model  # gemini-3-pro-preview

    async def engage(
        self,
        message: Message,
        history: list[ConversationMessage],
        metadata: Metadata,
        detection: DetectionResult,
        conversation_id: str | None = None,
    ) -> EngagementResult:
        """
        Engage with the scammer and generate a response.

        Args:
            message: The current scammer message
            history: Previous conversation messages
            metadata: Message metadata
            detection: Scam detection result
            conversation_id: Optional existing conversation ID

        Returns:
            EngagementResult with the agent's response
        """
        start_time = time.time()

        # Generate or use existing conversation ID
        conv_id = conversation_id or str(uuid.uuid4())

        self.logger.info(
            "Engaging with scammer",
            conversation_id=conv_id,
            history_length=len(history),
            confidence=detection.confidence,
        )

        # Determine engagement mode
        engagement_mode = self.policy.get_engagement_mode(detection.confidence)

        # Get/update persona state
        persona = self.persona_manager.update_persona(
            conv_id,
            scam_intensity=detection.confidence,
        )

        # Build conversation prompt for Gemini
        prompt = self._build_prompt(
            message=message,
            history=history,
            detection=detection,
            persona=persona,
        )

        # Generate response using Gemini 3 Pro
        try:
            response = await self._generate_response(prompt, persona)
        except Exception as e:
            self.logger.error("Failed to generate response", error=str(e))
            response = self._get_fallback_response(detection)

        # Calculate duration
        duration = int(time.time() - start_time)

        # Check if engagement should continue
        state = EngagementState(
            mode=engagement_mode,
            turn_count=persona.engagement_turn,
            duration_seconds=duration,
            intelligence_complete=False,  # Set by intelligence extractor
            scammer_suspicious=False,  # Detect from response patterns
            turns_since_new_info=0,  # Track over time
        )
        should_continue = self.policy.should_continue(state)
        exit_reason = self.policy.get_exit_reason(state) if not should_continue else None

        # Generate notes
        notes = self._generate_notes(detection, persona, engagement_mode)

        return EngagementResult(
            response=response,
            duration_seconds=duration,
            notes=notes,
            conversation_id=conv_id,
            turn_number=persona.engagement_turn,
            engagement_mode=engagement_mode,
            should_continue=should_continue,
            exit_reason=exit_reason,
        )

    def _build_prompt(
        self,
        message: Message,
        history: list[ConversationMessage],
        detection: DetectionResult,
        persona: Persona,
    ) -> str:
        """Build conversation prompt for Gemini."""
        # Format scam indicators
        scam_indicators = [m.description for m in detection.matched_patterns[:5]]
        indicators_text = format_scam_indicators(scam_indicators) if scam_indicators else "General suspicious behavior"

        # Format conversation history
        history_text = ""
        for msg in history[-10:]:  # Last 10 messages for context
            sender = "SCAMMER" if msg.sender == SenderType.SCAMMER else "YOU"
            history_text += f"[{sender}]: {msg.text}\n"

        prompt = f"""CONVERSATION HISTORY:
{history_text if history_text else "No previous messages"}

SCAMMER'S NEW MESSAGE:
"{message.text}"

YOUR TASK:
Generate a response as the naive, trusting victim. Your emotional state is: {persona.emotional_state.value}
This is turn {persona.engagement_turn} of the conversation.

Remember:
- Stay in character as a confused, worried person
- Ask questions that extract intelligence (bank accounts, UPI IDs, links)
- Keep responses short (1-3 sentences)
- Show willingness to comply but need guidance

DETECTED SCAM INDICATORS: {indicators_text}

Generate your response:"""

        return prompt

    async def _generate_response(
        self,
        prompt: str,
        persona: Persona,
    ) -> str:
        """Generate response using Gemini 3 Pro."""
        # Format system instruction with persona context
        system_instruction = HONEYPOT_SYSTEM_PROMPT.format(
            emotional_state=persona.emotional_state.value,
            turn_number=persona.engagement_turn,
            scam_indicators="See conversation context",
        )
        
        # Call Gemini 3 Pro with HIGH thinking for sophisticated responses
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                thinking_config=types.ThinkingConfig(
                    thinking_level=types.ThinkingLevel.HIGH  # Deep reasoning for believable responses
                ),
                temperature=self.settings.llm_temperature,
                max_output_tokens=256,  # Keep responses concise
            )
        )

        response_text = response.text

        # Add emotional modifier if appropriate
        if persona.engagement_turn > 0:
            modifier = persona.get_emotional_modifier()
            if modifier and not response_text.startswith(modifier):
                response_text = modifier + response_text

        # Potentially add extraction question
        if persona.should_ask_extraction_question():
            import random
            question = random.choice(EXTRACTION_QUESTIONS)
            if not any(q in response_text.lower() for q in ["account", "upi", "link", "number"]):
                response_text = response_text.rstrip(".")
                response_text += f" {question}"
                persona.record_extraction()

        return response_text

    def _get_fallback_response(self, detection: DetectionResult) -> str:
        """Get a fallback response if LLM fails."""
        fallback_responses = [
            "I'm sorry, I'm a bit confused. Can you explain that again?",
            "My phone is acting up. What do I need to do exactly?",
            "I didn't understand. Can you tell me step by step?",
            "Okay, but what should I do first? I'm worried.",
        ]
        import random
        return random.choice(fallback_responses)

    def _generate_notes(
        self, 
        detection: DetectionResult, 
        persona: Persona,
        mode: EngagementMode,
    ) -> str:
        """Generate agent notes summarizing the engagement."""
        notes_parts = []

        # Engagement mode
        notes_parts.append(f"Mode: {mode.value}")

        # Scam tactics detected
        categories_used = list(set(m.category.value for m in detection.matched_patterns))
        if categories_used:
            notes_parts.append(f"Tactics: {', '.join(categories_used)}")

        # Confidence
        notes_parts.append(f"Confidence: {detection.confidence:.0%}")

        # Engagement progress
        notes_parts.append(f"Turn: {persona.engagement_turn}")

        # Emotional state
        notes_parts.append(f"Persona: {persona.emotional_state.value}")

        return " | ".join(notes_parts)

    def end_conversation(self, conversation_id: str) -> None:
        """Clean up persona when conversation ends."""
        self.persona_manager.clear_persona(conversation_id)


# Singleton instance for reuse
_agent_instance: HoneypotAgent | None = None


def get_agent() -> HoneypotAgent:
    """Get or create the honeypot agent instance."""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = HoneypotAgent()
    return _agent_instance
```

### 4.5 Create Agent Module Init

#### src/agents/__init__.py

```python
"""Agent module for honeypot engagement."""

from src.agents.honeypot_agent import HoneypotAgent, EngagementResult, get_agent
from src.agents.persona import Persona, PersonaManager, PersonaTrait, EmotionalState
from src.agents.prompts import (
    HONEYPOT_SYSTEM_PROMPT,
    EXTRACTION_QUESTIONS,
    get_response_strategy,
)

__all__ = [
    "HoneypotAgent",
    "EngagementResult",
    "get_agent",
    "Persona",
    "PersonaManager",
    "PersonaTrait",
    "EmotionalState",
    "HONEYPOT_SYSTEM_PROMPT",
    "EXTRACTION_QUESTIONS",
    "get_response_strategy",
]
```

### 4.5 Write Agent Tests

#### tests/test_agent.py

```python
"""Tests for honeypot agent module."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.agents.honeypot_agent import HoneypotAgent, EngagementResult
from src.agents.persona import Persona, PersonaManager, EmotionalState, PersonaTrait
from src.agents.prompts import (
    get_response_strategy,
    format_scam_indicators,
    EXTRACTION_QUESTIONS,
)
from src.api.schemas import Message, ConversationMessage, Metadata, SenderType
from src.detection.detector import DetectionResult
from src.detection.patterns import ScamCategory, PatternMatch


class TestPersona:
    """Tests for Persona class."""

    def test_initial_state(self):
        """Persona should start with default values."""
        persona = Persona()
        assert persona.emotional_state == EmotionalState.CALM
        assert persona.engagement_turn == 0
        assert PersonaTrait.TRUSTING in persona.traits

    def test_emotional_state_updates_with_intensity(self):
        """Emotional state should reflect scam intensity."""
        persona = Persona()

        persona.update_emotional_state(0.9)
        assert persona.emotional_state == EmotionalState.PANICKED

        persona.update_emotional_state(0.6)
        assert persona.emotional_state == EmotionalState.ANXIOUS

        persona.update_emotional_state(0.3)
        assert persona.emotional_state == EmotionalState.CALM

    def test_increment_turn(self):
        """Turn counter should increment."""
        persona = Persona()
        assert persona.engagement_turn == 0

        persona.increment_turn()
        assert persona.engagement_turn == 1

        persona.increment_turn()
        assert persona.engagement_turn == 2

    def test_record_extraction(self):
        """Extraction count should track."""
        persona = Persona()
        assert persona.extracted_info_count == 0

        persona.record_extraction()
        assert persona.extracted_info_count == 1


class TestPersonaManager:
    """Tests for PersonaManager class."""

    def test_creates_new_persona(self):
        """Should create persona for new conversation."""
        manager = PersonaManager()
        persona = manager.get_or_create_persona("conv-123")

        assert persona is not None
        assert isinstance(persona, Persona)

    def test_returns_existing_persona(self):
        """Should return same persona for same conversation."""
        manager = PersonaManager()

        persona1 = manager.get_or_create_persona("conv-123")
        persona1.increment_turn()

        persona2 = manager.get_or_create_persona("conv-123")

        assert persona1 is persona2
        assert persona2.engagement_turn == 1

    def test_clear_persona(self):
        """Should remove persona when cleared."""
        manager = PersonaManager()

        manager.get_or_create_persona("conv-123")
        manager.clear_persona("conv-123")

        # Should create fresh persona
        new_persona = manager.get_or_create_persona("conv-123")
        assert new_persona.engagement_turn == 0


class TestPrompts:
    """Tests for prompt utilities."""

    def test_get_response_strategy_returns_list(self):
        """Should return response strategies."""
        strategies = get_response_strategy("urgency")
        assert isinstance(strategies, list)
        assert len(strategies) > 0

    def test_get_response_strategy_fallback(self):
        """Should return default for unknown category."""
        strategies = get_response_strategy("unknown")
        assert isinstance(strategies, list)

    def test_format_scam_indicators_empty(self):
        """Should handle empty indicators."""
        result = format_scam_indicators([])
        assert "detected" in result.lower()

    def test_format_scam_indicators_list(self):
        """Should format indicator list."""
        result = format_scam_indicators(["urgency", "authority"])
        assert "urgency" in result
        assert "authority" in result


class TestHoneypotAgent:
    """Tests for HoneypotAgent class."""

    @pytest.fixture
    def mock_detection(self) -> DetectionResult:
        """Create mock detection result."""
        return DetectionResult(
            is_scam=True,
            confidence=0.85,
            matched_patterns=[
                PatternMatch(
                    category=ScamCategory.URGENCY,
                    matched_text="immediately",
                    weight=0.7,
                    description="Urgency tactics",
                ),
            ],
            category_scores={ScamCategory.URGENCY: 0.7},
            reasoning="Scam detected",
        )

    @pytest.fixture
    def mock_message(self) -> Message:
        """Create mock message."""
        return Message(
            sender=SenderType.SCAMMER,
            text="Your account will be blocked! Share OTP immediately!",
            timestamp=datetime.now(),
        )

    @pytest.fixture
    def mock_metadata(self) -> Metadata:
        """Create mock metadata."""
        return Metadata(channel="SMS", language="English", locale="IN")

    @patch("src.agents.honeypot_agent.ChatVertexAI")
    @pytest.mark.asyncio
    async def test_engage_returns_result(
        self,
        mock_llm_class,
        mock_message: Message,
        mock_metadata: Metadata,
        mock_detection: DetectionResult,
    ):
        """Agent engagement should return valid result."""
        # Setup mock LLM
        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(
            return_value=MagicMock(content="Oh no! What should I do?")
        )
        mock_llm_class.return_value = mock_llm

        agent = HoneypotAgent()
        result = await agent.engage(
            message=mock_message,
            history=[],
            metadata=mock_metadata,
            detection=mock_detection,
        )

        assert isinstance(result, EngagementResult)
        assert result.response != ""
        assert result.conversation_id != ""
        assert result.duration_seconds >= 0

    @patch("src.agents.honeypot_agent.ChatVertexAI")
    @pytest.mark.asyncio
    async def test_engage_uses_history(
        self,
        mock_llm_class,
        mock_message: Message,
        mock_metadata: Metadata,
        mock_detection: DetectionResult,
    ):
        """Agent should use conversation history."""
        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(
            return_value=MagicMock(content="I understand, please help me.")
        )
        mock_llm_class.return_value = mock_llm

        history = [
            ConversationMessage(
                sender=SenderType.SCAMMER,
                text="Your account has issues",
                timestamp=datetime.now(),
            ),
            ConversationMessage(
                sender=SenderType.USER,
                text="What issues?",
                timestamp=datetime.now(),
            ),
        ]

        agent = HoneypotAgent()
        result = await agent.engage(
            message=mock_message,
            history=history,
            metadata=mock_metadata,
            detection=mock_detection,
        )

        # Verify LLM was called with history
        mock_llm.ainvoke.assert_called_once()
        call_messages = mock_llm.ainvoke.call_args[0][0]
        assert len(call_messages) > 2  # System + history + current

    @patch("src.agents.honeypot_agent.ChatVertexAI")
    @pytest.mark.asyncio
    async def test_fallback_on_llm_error(
        self,
        mock_llm_class,
        mock_message: Message,
        mock_metadata: Metadata,
        mock_detection: DetectionResult,
    ):
        """Should return fallback response on LLM error."""
        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(side_effect=Exception("LLM Error"))
        mock_llm_class.return_value = mock_llm

        agent = HoneypotAgent()
        result = await agent.engage(
            message=mock_message,
            history=[],
            metadata=mock_metadata,
            detection=mock_detection,
        )

        # Should still return a valid response
        assert result.response != ""
        assert len(result.response) > 10
```

## Verification Checklist

- [ ] `src/agents/prompts.py` defines system prompts and strategies
- [ ] `src/agents/persona.py` manages persona state across turns
- [ ] `src/agents/honeypot_agent.py` implements full agent logic
- [ ] Agent uses Vertex AI (Gemini) 
- [ ] Responses maintain human persona (never reveal detection)
- [ ] Extraction questions integrated naturally
- [ ] Emotional state evolves based on scam intensity
- [ ] Fallback responses work when LLM fails
- [ ] All tests pass: `pytest tests/test_agent.py -v`

## Integration Testing

```bash
# Set up environment variables
export GOOGLE_CLOUD_PROJECT=your-project
export GOOGLE_APPLICATION_CREDENTIALS=./secrets/service-account.json

# Test agent directly
python -c "
import asyncio
from src.agents.honeypot_agent import HoneypotAgent
from src.api.schemas import Message, Metadata, SenderType
from src.detection.detector import DetectionResult
from datetime import datetime

agent = HoneypotAgent()

message = Message(
    sender=SenderType.SCAMMER,
    text='Your SBI account is blocked! Share OTP now!',
    timestamp=datetime.now()
)

detection = DetectionResult(
    is_scam=True,
    confidence=0.9,
    matched_patterns=[],
    category_scores={},
    reasoning='Test'
)

result = asyncio.run(agent.engage(
    message=message,
    history=[],
    metadata=Metadata(),
    detection=detection
))

print(f'Response: {result.response}')
print(f'Notes: {result.notes}')
"
```

## Next Steps

After completing this milestone, proceed to **Milestone 5: Intelligence Extraction** to implement bank account, UPI ID, and URL extraction.
