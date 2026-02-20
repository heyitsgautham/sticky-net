"""
Scammer Simulator — drives multi-turn conversations against the API.

Sends template-based scammer messages from scenario JSON files to the
/api/v1/analyze endpoint via FastAPI TestClient and collects responses.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from starlette.testclient import TestClient


@dataclass
class ConversationResult:
    """Result of a full multi-turn conversation."""

    session_id: str = ""
    scenario_id: str = ""
    responses: list[dict] = field(default_factory=list)  # raw API responses
    replies: list[str] = field(default_factory=list)  # extracted reply texts
    conversation_history: list[dict] = field(default_factory=list)
    total_messages: int = 0
    duration_seconds: float = 0.0
    errors: list[str] = field(default_factory=list)
    turn_timings: list[float] = field(default_factory=list)  # per-turn latency


class ScammerSimulator:
    """Drives a multi-turn scam conversation using pre-scripted messages."""

    def __init__(
        self,
        client: TestClient,
        headers: dict[str, str],
        *,
        inter_turn_delay: float = 0.0,
    ):
        self.client = client
        self.headers = headers
        self.inter_turn_delay = inter_turn_delay

    def run_scenario(self, scenario: dict) -> ConversationResult:
        """
        Execute a full multi-turn scenario.

        scenario must have:
          - scenarioId: str
          - metadata: {channel, language, locale}
          - turns: [{turn: int, scammer_message: str, ...}, ...]
          OR
          - initialMessage: str  (+ optional turns for follow-ups)
          - fakeData: {bankAccount?, upiId?, phoneNumber?, ...}
        """
        session_id = str(uuid.uuid4())
        result = ConversationResult(
            session_id=session_id,
            scenario_id=scenario.get("scenarioId", "unknown"),
        )

        metadata = scenario.get("metadata", {
            "channel": "SMS",
            "language": "English",
            "locale": "IN",
        })

        # Build turn messages
        turns = scenario.get("turns", [])
        if not turns and "initialMessage" in scenario:
            # Build turns from initialMessage + follow-up builder
            turns = self._build_turns_from_scenario(scenario)

        conversation_history: list[dict] = []
        start_time = time.time()
        base_ts = datetime(2026, 1, 21, 10, 0, 0, tzinfo=timezone.utc)

        for i, turn_data in enumerate(turns):
            turn_num = turn_data.get("turn", i + 1)
            scammer_text = turn_data.get("scammer_message", "")
            if not scammer_text:
                continue

            # Build message object
            msg_ts = base_ts + timedelta(seconds=30 * (2 * i))
            message = {
                "sender": "scammer",
                "text": scammer_text,
                "timestamp": msg_ts.isoformat(),
            }

            # Build request body
            request_body = {
                "sessionId": session_id,
                "message": message,
                "conversationHistory": conversation_history.copy(),
                "metadata": metadata,
            }

            # Send request
            turn_start = time.time()
            try:
                resp = self.client.post(
                    "/api/v1/analyze",
                    json=request_body,
                    headers=self.headers,
                    timeout=30,
                )
                turn_latency = time.time() - turn_start
                result.turn_timings.append(turn_latency)

                if resp.status_code != 200:
                    result.errors.append(
                        f"Turn {turn_num}: HTTP {resp.status_code} — {resp.text[:200]}"
                    )
                    continue

                resp_data = resp.json()
                result.responses.append(resp_data)

                # Extract reply (GUVI checks: reply → message → text)
                reply = (
                    resp_data.get("reply")
                    or resp_data.get("message")
                    or resp_data.get("text")
                    or ""
                )
                result.replies.append(reply)

                if not reply:
                    result.errors.append(
                        f"Turn {turn_num}: No reply/message/text in response"
                    )

                # Update conversation history
                conversation_history.append(message)
                reply_ts = base_ts + timedelta(seconds=30 * (2 * i + 1))
                conversation_history.append({
                    "sender": "user",
                    "text": reply,
                    "timestamp": reply_ts.isoformat(),
                })

            except Exception as e:
                turn_latency = time.time() - turn_start
                result.turn_timings.append(turn_latency)
                result.errors.append(f"Turn {turn_num}: Exception — {e}")

            # Inter-turn delay
            if self.inter_turn_delay > 0:
                time.sleep(self.inter_turn_delay)

        result.conversation_history = conversation_history
        result.total_messages = len(conversation_history)
        result.duration_seconds = time.time() - start_time
        return result

    def _build_turns_from_scenario(self, scenario: dict) -> list[dict]:
        """Build turn list from initialMessage + fakeData-based follow-ups."""
        turns = [{"turn": 1, "scammer_message": scenario["initialMessage"]}]
        fake_data = scenario.get("fakeData", {})
        followups = _build_followups_from_fake_data(
            scenario.get("scenarioId", ""),
            scenario.get("scamType", ""),
            fake_data,
        )
        for i, msg in enumerate(followups):
            turns.append({"turn": i + 2, "scammer_message": msg})
        return turns


def _build_followups_from_fake_data(
    scenario_id: str,
    scam_type: str,
    fake_data: dict,
) -> list[str]:
    """Generate template-based follow-up messages embedding fakeData values."""
    messages = []

    bank = fake_data.get("bankAccount", "")
    upi = fake_data.get("upiId", "")
    phone = fake_data.get("phoneNumber", "")
    link = fake_data.get("phishingLink", "")
    email = fake_data.get("emailAddress", "")

    # Turn 2: build trust / introduce phone
    if phone:
        messages.append(
            f"Sir/Madam, I am calling from the official department. "
            f"You can verify by calling me at {phone}. Please hurry, time is limited."
        )
    else:
        messages.append(
            "Sir/Madam, this is very urgent. Please cooperate immediately "
            "or your account/offer will expire."
        )

    # Turn 3: introduce UPI / link
    if upi and bank:
        messages.append(
            f"I can see your account {bank} has a problem. "
            f"Please send Rs 1 to {upi} for verification."
        )
    elif upi:
        messages.append(
            f"To verify your identity, please send Rs 1 to our official UPI: {upi}. "
            f"This is standard procedure."
        )
    elif link:
        messages.append(
            f"Please click this link to proceed: {link}. "
            f"It is our official verification portal."
        )
    else:
        messages.append(
            "Please share your details immediately for verification. "
            "Your account safety depends on it."
        )

    # Turn 4: reinforce with more data
    parts = []
    if bank and bank not in str(messages):
        parts.append(f"Your account {bank} needs immediate action")
    if email:
        parts.append(f"you can also email us at {email}")
    if link and link not in str(messages):
        parts.append(f"visit {link} for secure access")
    if upi and upi not in str(messages):
        parts.append(f"our UPI is {upi}")
    if phone and phone not in str(messages):
        parts.append(f"call us at {phone}")

    if parts:
        messages.append(". ".join(parts) + ". Please act NOW!")
    else:
        messages.append("Time is running out! You must act immediately or face consequences.")

    # Turn 5: urgency / last chance
    messages.append(
        "This is your FINAL WARNING. If you do not comply within 5 minutes, "
        "we will have to take strict action. You have been warned."
    )

    return messages
