"""One scammer turn, from detection to validated intelligence, without any HTTP.

The analyze routes in ``src/api/routes.py`` parse the request, call these steps in
order and shape the response. Everything between, which detector verdict to keep,
how long the agent may take, how the LLM extraction and the regex backup combine
and how the agent notes are written, lives here so both routes share one copy.
"""

import asyncio
import random
import time
import uuid
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import Any

import structlog
from structlog.stdlib import BoundLogger

from src.agents.honeypot_agent import EngagementResult, HoneypotAgent
from src.agents.policy import EngagementMode
from src.api.final_output import history_as_dicts, merge_regex_backup, missing_intel
from src.api.schemas import AnalyzeRequest, ExtractedIntelligence, SenderType
from src.api.session_store import (
    get_or_init_session_intel,
    get_previous_detection,
    store_detection_result,
)
from src.detection.detector import DetectionResult, ScamDetector
from src.intelligence.extractor import IntelligenceExtractor
from src.metrics import record_fallback, record_verdict

logger = structlog.get_logger()

# Replies when the agent misses its time budget. They stall in the persona's voice.
TIMEOUT_REPLIES = (
    "hello... sorry i got disconnected for a moment... what were you saying?",
    "oh sorry my phone battery low... can you repeat that please?",
    "sorry beta network problem here... what did you say about my account?",
    "ji haan... sorry i missed that... can you tell me again please?",
)
EMPTY_REPLY_FALLBACK = "Sorry, I'm having trouble understanding. Can you repeat that?"

# The agent always gets at least this long, however late in the budget it starts.
MIN_AGENT_SECONDS = 1.0


def scammer_turn_number(request: AnalyzeRequest) -> int:
    """1-based turn number: scammer messages in the history plus the current one."""
    earlier = sum(1 for m in request.conversationHistory if m.sender == SenderType.SCAMMER)
    return earlier + 1


def messages_exchanged(request: AnalyzeRequest) -> int:
    """History length plus the current message and the agent's reply."""
    return len(request.conversationHistory) + 2


@dataclass(frozen=True)
class EngagedTurn:
    """The agent's side of a scam turn, ready for the routes to shape into a reply."""

    engagement: EngagementResult
    reply: str
    intel: ExtractedIntelligence
    notes: str
    turn_number: int


class TurnPipeline:
    """Runs the detect, engage and extract steps of one turn for one session."""

    def __init__(
        self,
        detector: ScamDetector,
        agent_factory: Callable[[], HoneypotAgent],
        session_id: str,
        endpoint: str,
        log: BoundLogger | None = None,
    ) -> None:
        self.detector = detector
        # Resolved on first engage, so a harmless message never builds the agent
        # and its Gemini client.
        self._agent_factory = agent_factory
        self.session_id = session_id
        self.endpoint = endpoint
        self.log: BoundLogger = log or logger.bind(session_id=session_id)
        self.extractor = IntelligenceExtractor()

    async def detect(self, request: AnalyzeRequest) -> DetectionResult:
        """Classify the message. A session flagged once stays flagged on later turns."""
        result = await self.detector.analyze(
            message=request.message.text,
            history=request.conversationHistory,
            metadata=request.metadata,
            previous_result=get_previous_detection(self.session_id),
        )
        store_detection_result(self.session_id, result)
        record_verdict(self.endpoint, result.is_scam, result.scam_type)
        return result

    async def engage(
        self,
        request: AnalyzeRequest,
        detection: DetectionResult,
        *,
        deadline: float | None = None,
        share_session_intel: bool = False,
    ) -> EngagedTurn:
        """Get the agent's reply and the turn's validated intelligence.

        ``deadline`` is a ``time.time()`` value; past it the agent is cancelled and a
        stalling reply is used. ``share_session_intel`` tells the agent which intel
        the session already holds, so it asks for what is still missing.
        """
        turn = scammer_turn_number(request)
        missing: list[str] | None = None
        known: dict[str, list[str]] | None = None
        if share_session_intel:
            session_intel = get_or_init_session_intel(self.session_id)
            missing = missing_intel(session_intel)
            known = {k: list(v) for k, v in session_intel.items()}

        agent = self._agent_factory()
        engage = agent.engage(
            message=request.message,
            history=request.conversationHistory,
            metadata=request.metadata,
            detection=detection,
            turn_number=turn,
            missing_intel=missing,
            extracted_intel=known,
        )
        if deadline is None:
            engagement = await engage
        else:
            engagement = await self._engage_before(engage, deadline, turn)

        self.log.info(
            "Agent engagement complete",
            agent_response=engagement.response or None,
            has_extracted_intel=engagement.extracted_intelligence is not None,
        )
        intel = self.collect_intel(request, engagement)

        reply = engagement.response
        if not reply:
            reply = EMPTY_REPLY_FALLBACK
            record_fallback("empty_reply")
            self.log.warning("Agent response was None, using fallback")

        notes = agent.notes_for(engagement, detection, turn, intel)
        return EngagedTurn(engagement, reply, intel, notes, turn)

    async def _engage_before(
        self,
        engage: Coroutine[Any, Any, EngagementResult],
        deadline: float,
        turn: int,
    ) -> EngagementResult:
        """Await ``engage`` until ``deadline``, then fall back to a stalling reply."""
        budget = max(MIN_AGENT_SECONDS, deadline - time.time())
        try:
            return await asyncio.wait_for(engage, timeout=budget)
        except TimeoutError:
            record_fallback("agent_timeout")
            self.log.warning("Agent timed out, using fallback", budget=budget)
            return EngagementResult(
                response=random.choice(TIMEOUT_REPLIES),
                duration_seconds=int(budget),
                notes="Agent timed out; fallback response used",
                conversation_id=str(uuid.uuid4()),
                turn_number=turn,
                engagement_mode=EngagementMode.AGGRESSIVE,
                should_continue=True,
                extracted_intelligence=None,
            )

    def collect_intel(
        self, request: AnalyzeRequest, engagement: EngagementResult
    ) -> ExtractedIntelligence:
        """Validate the LLM's extraction, then add what a regex pass over the chat finds."""
        if engagement.extracted_intelligence:
            intel = self.extractor.validate_llm_extraction(engagement.extracted_intelligence)
            self.log.info(
                "AI extraction validated",
                bank_accounts=len(intel.bankAccounts),
                upi_ids=len(intel.upiIds),
                phone_numbers=len(intel.phoneNumbers),
                beneficiary_names=len(intel.beneficiaryNames),
                ifsc_codes=len(intel.ifscCodes),
                urls=len(intel.phishingLinks),
                case_ids=len(intel.caseIds),
                policy_numbers=len(intel.policyNumbers),
                order_numbers=len(intel.orderNumbers),
            )
        else:
            intel = ExtractedIntelligence()
            self.log.warning("No AI extraction available")

        regex_result = self.extractor.extract_from_conversation(
            history_as_dicts(request, include_current=True)
        )
        if regex_result.has_intelligence:
            self.log.info(
                "Regex backup found additional intel",
                phones=len(regex_result.phone_numbers),
                accounts=len(regex_result.bank_accounts),
                upi=len(regex_result.upi_ids),
                urls=len(regex_result.phishing_links),
                emails=len(regex_result.emails),
            )
        return merge_regex_backup(intel, regex_result)
