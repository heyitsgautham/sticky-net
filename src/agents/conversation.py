"""Per-turn prompt text and engagement notes for the honeypot agent."""

import re

from src.agents.persona import Persona
from src.agents.policy import EngagementMode
from src.api.schemas import ConversationMessage, ExtractedIntelligence, Message, SenderType
from src.detection.detector import DetectionResult


def summarize_earlier_turns(truncated_turns: list[ConversationMessage]) -> str:
    """Generate a concise summary of earlier conversation turns that were
    dropped due to context window limits.

    This preserves key intelligence and context so the agent doesn't
    repeat itself or lose track of what was discussed.

    Args:
        truncated_turns: The older turns that will NOT be included in
                         the full conversation history.

    Returns:
        A short natural-language summary (< 200 words).
    """
    if not truncated_turns:
        return ""

    # Patterns to detect key intel in older messages
    PHONE_RE = re.compile(r"\+?91[-\s]?\d{10}|\b\d{10}\b")
    UPI_RE = re.compile(r"[\w.-]+@[a-zA-Z]{2,}")
    URL_RE = re.compile(r"https?://[^\s]+", re.IGNORECASE)
    EMAIL_RE = re.compile(r"[\w.-]+@[\w.-]+\.\w{2,}")

    scammer_claims: list[str] = []
    agent_actions: list[str] = []
    intel_found: list[str] = []

    for msg in truncated_turns:
        text = msg.text
        sender = msg.sender

        is_scammer = (
            sender == SenderType.SCAMMER
            or (hasattr(sender, "value") and sender.value == "scammer")
            or str(sender).lower() == "scammer"
        )

        if is_scammer:
            phones = PHONE_RE.findall(text)
            upis = UPI_RE.findall(text)
            urls = URL_RE.findall(text)
            emails = EMAIL_RE.findall(text)

            if phones:
                intel_found.append(f"phone: {', '.join(phones)}")
            if upis:
                intel_found.append(f"UPI: {', '.join(upis)}")
            if urls:
                intel_found.append(f"link: {', '.join(urls)}")
            if emails:
                intel_found.append(f"email: {', '.join(emails)}")

            gist = text[:80].strip()
            if len(text) > 80:
                gist += "..."
            scammer_claims.append(gist)
        else:
            gist = text[:60].strip()
            if len(text) > 60:
                gist += "..."
            agent_actions.append(gist)

    parts: list[str] = []
    parts.append(f"[SUMMARY OF EARLIER {len(truncated_turns)} MESSAGES]")

    if scammer_claims:
        parts.append("Scammer said: " + " | ".join(scammer_claims[:4]))

    if agent_actions:
        parts.append("You replied: " + " | ".join(agent_actions[:3]))

    if intel_found:
        parts.append("Intel found in earlier turns: " + "; ".join(set(intel_found)))

    summary = "\n".join(parts)

    # Enforce word budget
    words = summary.split()
    if len(words) > 200:
        summary = " ".join(words[:200]) + "..."

    return summary


def build_turn_prompt(message: Message, history: list[ConversationMessage], max_turns: int) -> str:
    """Build the user prompt for one turn: recent history plus the new message.

    History beyond ``max_turns`` is folded into a short summary to keep latency down.
    """

    # If history exceeds context window, generate summary of older turns
    summary_text = ""
    if len(history) > max_turns:
        older_turns = history[:-max_turns]
        summary_text = summarize_earlier_turns(older_turns)
        truncated_history = history[-max_turns:]
    else:
        truncated_history = history

    # Format conversation history
    history_text = ""
    for msg in truncated_history:
        sender = "SCAMMER" if msg.sender == SenderType.SCAMMER else "YOU"
        history_text += f"[{sender}]: {msg.text}\n"

    # Build prompt with optional summary
    if summary_text:
        prompt = f"""{summary_text}

RECENT CONVERSATION HISTORY:
{history_text}

SCAMMER'S NEW MESSAGE:
"{message.text}"

Generate your response as Pushpa Verma:"""
    else:
        prompt = f"""CONVERSATION HISTORY:
{history_text if history_text else "No previous messages"}

SCAMMER'S NEW MESSAGE:
"{message.text}"

Generate your response as Pushpa Verma:"""

    return prompt


def engagement_notes(
    detection: DetectionResult,
    persona: Persona,
    mode: EngagementMode,
    turn_number: int,
    extracted_intel: ExtractedIntelligence | None = None,
) -> str:
    """One-line summary of the engagement for the callback and dashboard."""
    notes_parts = []

    # Engagement mode
    notes_parts.append(f"Mode: {mode.value}")

    # Scam type if detected
    if detection.scam_type:
        notes_parts.append(f"Type: {detection.scam_type}")

    # Confidence
    notes_parts.append(f"Confidence: {detection.confidence:.0%}")

    # Engagement progress - use the actual turn number passed in
    notes_parts.append(f"Turn: {turn_number}")

    # Emotional state
    notes_parts.append(f"Persona: {persona.emotional_state.value}")

    # Add intelligence extraction counts (only from scammer messages)
    if extracted_intel:
        intel_counts = []
        if extracted_intel.bankAccounts:
            intel_counts.append(f"{len(extracted_intel.bankAccounts)} Bank Account(s)")
        if extracted_intel.upiIds:
            intel_counts.append(f"{len(extracted_intel.upiIds)} UPI ID(s)")
        if extracted_intel.phoneNumbers:
            intel_counts.append(f"{len(extracted_intel.phoneNumbers)} Phone(s)")
        if extracted_intel.phishingLinks:
            intel_counts.append(f"{len(extracted_intel.phishingLinks)} URL(s)")
        if extracted_intel.emailAddresses:
            intel_counts.append(f"{len(extracted_intel.emailAddresses)} Email(s)")
        if extracted_intel.ifscCodes:
            intel_counts.append(f"{len(extracted_intel.ifscCodes)} IFSC Code(s)")
        if extracted_intel.whatsappNumbers:
            intel_counts.append(f"{len(extracted_intel.whatsappNumbers)} WhatsApp(s)")
        if extracted_intel.beneficiaryNames:
            intel_counts.append(f"{len(extracted_intel.beneficiaryNames)} Name(s)")
        if extracted_intel.caseIds:
            intel_counts.append(f"{len(extracted_intel.caseIds)} Case ID(s)")
        if extracted_intel.policyNumbers:
            intel_counts.append(f"{len(extracted_intel.policyNumbers)} Policy Number(s)")
        if extracted_intel.orderNumbers:
            intel_counts.append(f"{len(extracted_intel.orderNumbers)} Order Number(s)")

        if intel_counts:
            notes_parts.append(f"Extracted: {', '.join(intel_counts)}")

    return " | ".join(notes_parts)
