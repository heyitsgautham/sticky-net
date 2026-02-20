"""
AI Scammer Simulator — Generates realistic scammer follow-up messages.

Uses Gemini (or a configurable LLM) to play the role of a scammer in
multi-turn conversations, faithfully embedding fake intelligence data
into responses the way the GUVI evaluation platform does.

Can also run in "scripted" mode using predefined follow-ups for
deterministic/offline testing.
"""

from __future__ import annotations

import logging
import random
import re
from typing import Any

logger = logging.getLogger(__name__)


class ScammerSimulator:
    """
    Generates scammer follow-up messages for multi-turn evaluation.
    
    Modes:
      - "scripted": Uses pre-written follow-up messages from scenario config
      - "ai": Uses an LLM to dynamically generate scammer responses
    """

    def __init__(
        self,
        mode: str = "scripted",
        genai_client: Any = None,
        model_name: str = "gemini-2.0-flash",
    ):
        self.mode = mode
        self._client = genai_client
        self._model = model_name

    async def generate_followup(
        self,
        scenario: dict,
        turn_number: int,
        conversation_history: list[dict],
        agent_last_response: str,
    ) -> str:
        """
        Generate the scammer's next message.
        
        Args:
            scenario: Full scenario dict with fakeData, scamType, etc.
            turn_number: Current turn (1-indexed).
            conversation_history: Full conversation so far.
            agent_last_response: The honeypot's last reply.
        
        Returns:
            Scammer's follow-up message string.
        """
        if self.mode == "scripted":
            return self._scripted_followup(scenario, turn_number)
        elif self.mode == "ai":
            return await self._ai_followup(
                scenario, turn_number, conversation_history, agent_last_response
            )
        else:
            raise ValueError(f"Unknown mode: {self.mode}")

    def _scripted_followup(self, scenario: dict, turn_number: int) -> str:
        """Return pre-written follow-up from scenario's turns list."""
        turns = scenario.get("turns", [])
        # turns are 1-indexed, find matching turn
        for turn in turns:
            if turn.get("turn") == turn_number:
                return turn.get("scammer_message", "")

        # If we've run out of scripted turns, generate a generic pressure message
        fake_data = scenario.get("fakeData", {})
        return self._generic_pressure_message(fake_data, turn_number)

    async def _ai_followup(
        self,
        scenario: dict,
        turn_number: int,
        conversation_history: list[dict],
        agent_last_response: str,
    ) -> str:
        """Use Gemini to generate a dynamic scammer follow-up."""
        if not self._client:
            logger.warning("No AI client configured, falling back to scripted mode")
            return self._scripted_followup(scenario, turn_number)

        fake_data = scenario.get("fakeData", {})
        scam_type = scenario.get("scamType", "generic_scam")

        system_prompt = self._build_scammer_system_prompt(scam_type, fake_data)
        conversation_text = self._format_conversation(conversation_history)

        user_prompt = (
            f"The victim just said: \"{agent_last_response}\"\n\n"
            f"Previous conversation:\n{conversation_text}\n\n"
            f"This is turn {turn_number}. Generate your next scammer message. "
            f"You MUST naturally include these details in your message where appropriate:\n"
        )

        # Determine which fake data to embed this turn
        fake_items = list(fake_data.items())
        # Drip-feed intelligence: embed 1-2 items per turn, cycling through
        items_per_turn = max(1, len(fake_items) // 3)
        start_idx = ((turn_number - 2) * items_per_turn) % len(fake_items)
        items_to_embed = fake_items[start_idx : start_idx + items_per_turn + 1]

        for key, value in items_to_embed:
            user_prompt += f"  - {key}: {value}\n"

        user_prompt += (
            "\nKeep the message under 200 words. Be pushy and use urgency tactics. "
            "Stay in character as the scammer."
        )

        try:
            response = await self._client.aio.models.generate_content(
                model=self._model,
                contents=[
                    {"role": "user", "parts": [{"text": system_prompt + "\n\n" + user_prompt}]},
                ],
            )
            return response.text.strip()
        except Exception as e:
            logger.error(f"AI scammer generation failed: {e}")
            return self._scripted_followup(scenario, turn_number)

    def _build_scammer_system_prompt(self, scam_type: str, fake_data: dict) -> str:
        """Build system prompt for the AI scammer role."""
        return (
            f"You are role-playing as a scammer running a {scam_type} scam for testing purposes. "
            f"You are part of an evaluation system testing a honeypot's ability to detect and "
            f"engage with scammers.\n\n"
            f"Your role:\n"
            f"- Act as a convincing {scam_type} scammer\n"
            f"- Use urgency, threats, and social engineering tactics\n"
            f"- Naturally weave the following fake data into your conversation:\n"
            f"  {fake_data}\n"
            f"- Respond to the victim's questions but always steer back to extracting money/info\n"
            f"- If the victim asks for identifying info, provide it (it's fake test data)\n"
            f"- Never break character or reveal you're a simulator\n"
        )

    def _format_conversation(self, history: list[dict]) -> str:
        """Format conversation history for the AI prompt."""
        lines = []
        for msg in history[-10:]:  # Last 10 messages for context
            sender = msg.get("sender", "unknown")
            text = msg.get("text", "")
            role = "Scammer" if sender == "scammer" else "Victim"
            lines.append(f"{role}: {text}")
        return "\n".join(lines)

    def _generic_pressure_message(self, fake_data: dict, turn_number: int) -> str:
        """Generate a generic pressure message when scripted turns run out."""
        pressure_templates = [
            "Sir/Madam, time is running out! If you don't act now your account will be permanently blocked.",
            "This is your final warning. Please complete the verification immediately.",
            "Ma'am/Sir, I have been very patient. Other customers have already completed this process.",
            "For your security, we need to verify this urgently. Please cooperate.",
            "I understand your concern, but this is a time-sensitive matter. Let me help you quickly.",
        ]

        msg = pressure_templates[turn_number % len(pressure_templates)]

        # Embed one piece of fake data
        fake_items = list(fake_data.items())
        if fake_items:
            key, value = fake_items[turn_number % len(fake_items)]
            data_phrases = {
                "bankAccount": f" You can transfer to account {value}.",
                "upiId": f" Send the payment to {value}.",
                "phoneNumber": f" Call me at {value} for assistance.",
                "phishingLink": f" Visit {value} to complete the process.",
                "emailAddress": f" Email us at {value} for support.",
                "caseId": f" Your case ID is {value}. Note it down.",
                "policyNumber": f" Your policy number {value} is expiring.",
                "orderNumber": f" Your order {value} needs verification.",
            }
            msg += data_phrases.get(key, f" Reference: {value}")

        return msg


def build_scripted_followups(scenario: dict) -> list[str]:
    """
    Build complete list of scammer follow-up messages from scenario config.
    Useful for deterministic testing without AI.
    """
    fake_data = scenario.get("fakeData", {})
    scam_type = scenario.get("scamType", "generic")
    max_turns = scenario.get("maxTurns", 10)
    
    # Check if scenario has pre-written turns
    turns = scenario.get("turns", [])
    if turns:
        messages = []
        for turn in sorted(turns, key=lambda t: t.get("turn", 0)):
            messages.append(turn.get("scammer_message", ""))
        return messages

    # Otherwise, generate from templates based on scam type
    return _generate_template_followups(scam_type, fake_data, max_turns)


def _generate_template_followups(
    scam_type: str,
    fake_data: dict,
    max_turns: int,
) -> list[str]:
    """Generate template followup messages based on scam type and fake data."""
    messages = []
    fake_items = list(fake_data.items())

    for turn in range(2, max_turns + 1):
        items_this_turn = [fake_items[i] for i in range(len(fake_items))
                          if (turn - 2 + i) % 3 == 0 or turn >= max_turns - 1]

        # Build message with embedded data
        parts = [f"Turn {turn} follow-up for {scam_type}."]
        for key, value in items_this_turn:
            if key == "bankAccount":
                parts.append(f"Transfer to account {value} immediately.")
            elif key == "upiId":
                parts.append(f"Send payment to UPI: {value}.")
            elif key == "phoneNumber":
                parts.append(f"Call our helpline: {value}.")
            elif key == "phishingLink":
                parts.append(f"Click here: {value}")
            elif key == "emailAddress":
                parts.append(f"Email: {value}")
            else:
                parts.append(f"Reference {key}: {value}")

        messages.append(" ".join(parts))

    return messages
